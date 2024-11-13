import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import discord
from discord import Intents
import asyncio
import os
import math
import threading
import io
import configparser
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageTk

CHUNK_SIZE = 8 * 1024 * 1024

class DiscordCloudStorage:
    def __init__(self, master):
        self.master = master
        self.master.title("DisCloud")
        self.master.geometry("900x600")
        self.master.configure(bg="#2C2F33")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.icon_cache = {}
        self.setup_icons()

        self.setup_ui()
        self.load_settings()

        intents = Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.channel = None
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.setup_discord_events()

    def setup_icons(self):
        icon_size = (16, 16)
        icons = {
            'folder': '📁', 'file': '📄', 'image': '🖼️',
            'video': '🎞️', 'audio': '🎵', 'document': '📑'
        }
        for name, char in icons.items():
            img = Image.new('RGBA', icon_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((0, 0), char, fill="white")
            self.icon_cache[name] = ImageTk.PhotoImage(img)

    def setup_ui(self):
        self.tab_control = ctk.CTkTabview(self.master)
        self.tab_control.pack(expand=True, fill="both", padx=10, pady=10)

        self.upload_tab = self.tab_control.add("Upload File")
        self.manage_tab = self.tab_control.add("Manage Files")
        self.settings_tab = self.tab_control.add("Settings")

        self.setup_upload_tab()
        self.setup_manage_tab()
        self.setup_settings_tab()

    def setup_upload_tab(self):
        self.file_path = tk.StringVar()
        ctk.CTkLabel(self.upload_tab, text="Select File:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(self.upload_tab, textvariable=self.file_path, width=400).grid(row=0, column=1, padx=10, pady=10)
        ctk.CTkButton(self.upload_tab, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=10, pady=10)

        ctk.CTkButton(self.upload_tab, text="Upload", command=self.start_upload).grid(row=1, column=1, pady=20)

        self.progress = ctk.CTkProgressBar(self.upload_tab, width=400)
        self.progress.grid(row=2, column=0, columnspan=3, padx=10, pady=10)
        self.progress.set(0)

        self.status_var = tk.StringVar()
        ctk.CTkLabel(self.upload_tab, textvariable=self.status_var).grid(row=3, column=0, columnspan=3, pady=10)

    def setup_manage_tab(self):
        search_frame = ctk.CTkFrame(self.manage_tab)
        search_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=200)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.search_files)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                        background="#2a2d2e", 
                        foreground="white", 
                        fieldbackground="#2a2d2e",
                        borderwidth=0,
                        font=('TkDefaultFont', 10))
        style.map('Treeview', background=[('selected', '#22559b')])
        style.configure("Treeview.Heading", 
                        background="#1f1f1f", 
                        foreground="white", 
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[('active', '#3484F0')])

        self.file_list = ttk.Treeview(self.manage_tab, columns=("Name", "Size", "Chunks"), show="headings")
        self.file_list.heading("Name", text="Name")
        self.file_list.heading("Size", text="Size")
        self.file_list.heading("Chunks", text="Chunks")
        self.file_list.column("Name", width=400)
        self.file_list.column("Size", width=100)
        self.file_list.column("Chunks", width=100)
        self.file_list.pack(expand=True, fill="both", padx=10, pady=10)

        button_frame = ctk.CTkFrame(self.manage_tab)
        button_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(button_frame, text="Download", command=self.download_file).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Delete", command=self.delete_file).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Refresh", command=self.refresh_file_list).pack(side="left", padx=5)

    def setup_settings_tab(self):
        self.token_var = tk.StringVar()
        self.channel_id_var = tk.StringVar()

        ctk.CTkLabel(self.settings_tab, text="Discord Bot Token:").pack(anchor="w", padx=10, pady=5)
        ctk.CTkEntry(self.settings_tab, textvariable=self.token_var, show="*", width=400).pack(padx=10, pady=5)

        ctk.CTkLabel(self.settings_tab, text="Discord Channel ID:").pack(anchor="w", padx=10, pady=5)
        ctk.CTkEntry(self.settings_tab, textvariable=self.channel_id_var, width=400).pack(padx=10, pady=5)

        ctk.CTkButton(self.settings_tab, text="Save Settings", command=self.save_settings).pack(pady=20)

    def setup_discord_events(self):
        @self.client.event
        async def on_ready():
            self.channel = self.client.get_channel(int(self.channel_id_var.get()))
            if not self.channel:
                self.status_var.set("Error: Invalid channel ID")
            else:
                self.status_var.set("Connected to Discord")
                await self._update_file_list()

    def browse_file(self):
        filename = filedialog.askopenfilename()
        self.file_path.set(filename)

    def start_upload(self):
        file_path = self.file_path.get()
        if not file_path:
            self.status_var.set("Please select a file to upload.")
            return

        future = asyncio.run_coroutine_threadsafe(self._upload_file(file_path), self.loop)
        future.add_done_callback(lambda f: self.handle_async_result(f, "File upload"))

    async def _upload_file(self, file_path):
        if not self.channel:
            raise Exception("Discord channel not set.")

        file_size = os.path.getsize(file_path)
        num_chunks = math.ceil(file_size / CHUNK_SIZE)
        
        self.progress.set(0)
        
        async with aiofiles.open(file_path, 'rb') as file:
            file_name = os.path.basename(file_path)
            await self.channel.send(f"Uploading file: {file_name}")
            
            for i in range(num_chunks):
                chunk = await file.read(CHUNK_SIZE)
                chunk_file = discord.File(io.BytesIO(chunk), filename=f"{file_name}.part{i}")
                await self.channel.send(file=chunk_file)
                
                self.progress.set((i + 1) / num_chunks)
                self.status_var.set(f"Uploaded chunk {i+1}/{num_chunks}")
            
        await self.channel.send(f"Upload complete: {file_name}")
        self.status_var.set("Upload complete!")
        await self._update_file_list()

    def download_file(self):
        selected_item = self.file_list.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a file to download.")
            return

        file_name = self.file_list.item(selected_item)['values'][0]
        save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=file_name)
        if save_path:
            future = asyncio.run_coroutine_threadsafe(self._download_and_reassemble(file_name, save_path), self.loop)
            future.add_done_callback(lambda f: self.handle_async_result(f, "File download"))

    async def _download_and_reassemble(self, file_name, save_path):
        file_messages = []
        async for message in self.channel.history(limit=None):
            if message.attachments and message.attachments[0].filename.startswith(file_name):
                file_messages.append(message)
        
        file_messages.sort(key=lambda msg: int(msg.attachments[0].filename.split('part')[-1]))

        async with aiofiles.open(save_path, 'wb') as output_file:
            for msg in file_messages:
                attachment = msg.attachments[0]
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            chunk = await resp.read()
                            await output_file.write(chunk)

        self.status_var.set(f"File downloaded and reassembled: {save_path}")

    def delete_file(self):
        selected_item = self.file_list.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a file to delete.")
            return

        file_name = self.file_list.item(selected_item)['values'][0]
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {file_name}?"):
            future = asyncio.run_coroutine_threadsafe(self._delete_file_chunks(file_name), self.loop)
            future.add_done_callback(lambda f: self.handle_async_result(f, "File deletion"))

    async def _delete_file_chunks(self, file_name):
        async for message in self.channel.history(limit=None):
            if message.attachments and message.attachments[0].filename.startswith(file_name):
                await message.delete()

        self.status_var.set(f"File deleted: {file_name}")
        await self._update_file_list()

    def refresh_file_list(self):
        self.file_list.delete(*self.file_list.get_children())
        future = asyncio.run_coroutine_threadsafe(self._update_file_list(), self.loop)
        future.add_done_callback(lambda f: self.handle_async_result(f, "File list refresh"))

    def get_file_icon(self, file_name):
        extension = os.path.splitext(file_name)[1].lower()
        if extension in ['.jpg', '.jpeg', '.png', '.gif']:
            return self.icon_cache['image']
        elif extension in ['.mp3', '.wav', '.ogg']:
            return self.icon_cache['audio']
        elif extension in ['.mp4', '.avi', '.mov']:
            return self.icon_cache['video']
        elif extension in ['.txt', '.doc', '.docx', '.pdf']:
            return self.icon_cache['document']
        else:
            return self.icon_cache['file']

    async def _update_file_list(self):
        self.file_list.delete(*self.file_list.get_children())
        files = {}
        async for message in self.channel.history(limit=None):
            if message.attachments:
                for attachment in message.attachments:
                    file_name = attachment.filename.split('.part')[0]
                    if file_name not in files:
                        files[file_name] = {'size': 0, 'chunks': 0}
                    files[file_name]['size'] += attachment.size
                    files[file_name]['chunks'] += 1

        for file_name, info in files.items():
            icon = self.get_file_icon(file_name)
            size_kb = info['size'] / (1024*1024)
            self.file_list.insert("", "end", values=(file_name, f"{size_kb:.2f} MB", info['chunks']), image=icon)

    def search_files(self, event):
        search_term = self.search_var.get().lower()
        for item in self.file_list.get_children():
            file_name = self.file_list.item(item)['values'][0].lower()
            if search_term in file_name:
                self.file_list.item(item, tags=())
            else:
                self.file_list.item(item, tags=('hidden',))
        self.file_list.tag_configure('hidden', background='#2a2d2e')

    def save_settings(self):
        config = configparser.ConfigParser()
        config['DEFAULT'] = {
            'Token': self.token_var.get(),
            'ChannelID': self.channel_id_var.get()
        }
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        
        messagebox.showinfo("Settings Saved", "Settings have been saved. Please restart the application.")

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        if 'DEFAULT' in config:
            self.token_var.set(config['DEFAULT'].get('Token', ''))
            self.channel_id_var.set(config['DEFAULT'].get('ChannelID', ''))

    def handle_async_result(self, future, operation):
        try:
            future.result()
            self.status_var.set(f"{operation} completed successfully")
        except Exception as e:
            self.status_var.set(f"Error during {operation}: {str(e)}")

    async def start_client(self):
        await self.client.start(self.token_var.get())

    def run_discord_client(self):
        self.loop.run_until_complete(self.start_client())

if __name__ == "__main__":
    root = ctk.CTk()
    app = DiscordCloudStorage(root)

    discord_thread = threading.Thread(target=app.run_discord_client, daemon=True)
    discord_thread.start()

    root.mainloop()