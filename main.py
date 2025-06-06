import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
import os
import yt_dlp

class ShortsDownloaderApp:
    def __init__(self, root):
        self.root = root
        root.title("Shorts Bulk Downloader By manishsharmag")
        root.geometry("700x250")
        root.configure(bg="#2E2E2E")

        # Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#2E2E2E", foreground="#FFFFFF", font=("Segoe UI", 10))
        style.configure("TButton", background="#555555", foreground="#FFFFFF", font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground="#555555", foreground="#FFFFFF", font=("Segoe UI", 10))
        style.configure("Horizontal.TProgressbar", troughcolor="#555555", bordercolor="#555555", background="#009688")
        style.configure("TFrame", background="#2E2E2E")

        self.main_frame = ttk.Frame(root, padding=15)
        self.main_frame.pack(expand=True, fill=tk.BOTH)

        # Folder Selection
        ttk.Label(self.main_frame, text="Select folder to save videos:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.folder_var = tk.StringVar()
        self.folder_entry = ttk.Entry(self.main_frame, textvariable=self.folder_var, width=50, state="readonly")
        self.folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        ttk.Button(self.main_frame, text="Browse", command=self.browse_folder).grid(row=0, column=2, padx=10)

        # Channel URL input
        ttk.Label(self.main_frame, text="Enter YouTube channel URL:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.channel_entry = ttk.Entry(self.main_frame, width=50)
        self.channel_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E))

        # Start button
        self.start_button = ttk.Button(self.main_frame, text="Start Download", command=self.start_download)
        self.start_button.grid(row=2, column=0, columnspan=3, pady=15, sticky=(tk.W, tk.E))

        # Progress bar and label
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(self.main_frame, orient="horizontal", mode="determinate",
                                            variable=self.progress_var, style="Horizontal.TProgressbar")
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E))

        self.progress_label_var = tk.StringVar()
        self.progress_label = ttk.Label(self.main_frame, textvariable=self.progress_label_var)
        self.progress_label.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        # Configure column weights for responsiveness
        self.main_frame.columnconfigure(1, weight=1)

        # Internal state
        self.video_count = 0

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_var.set(folder_selected)

    def start_download(self):
        folder = self.folder_var.get().strip()
        channel_url = self.channel_entry.get().strip()

        if not folder:
            messagebox.showerror("Error", "Please select a folder to save videos.")
            return
        if not channel_url:
            messagebox.showerror("Error", "Please enter a YouTube channel URL.")
            return

        # Create output folder if doesn't exist
        os.makedirs(folder, exist_ok=True)

        # Disable start button to prevent multiple clicks
        self.start_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label_var.set("Fetching shorts links...")

        # Run the download in a background thread
        Thread(target=self.download_shorts_from_channel, args=(channel_url, folder), daemon=True).start()

    def download_shorts_from_channel(self, channel_url, output_folder):
        try:
            shorts_links = self.get_all_shorts_links(channel_url)
            if not shorts_links:
                self.update_ui(lambda: [
                    self.progress_label_var.set("No shorts found on the channel."),
                    self.start_button.config(state=tk.NORMAL)
                ])
                return

            self.video_count = len(shorts_links)
            self.update_ui(lambda: self.progress_label_var.set(f"Found {self.video_count} shorts. Starting downloads..."))

            # Download videos one by one with progress callback
            for idx, video_url in enumerate(shorts_links, 1):
                self.download_video(video_url, output_folder, idx, self.video_count)

            self.update_ui(lambda: [
                self.progress_label_var.set("All downloads completed!"),
                self.progress_var.set(100),
                self.start_button.config(state=tk.NORMAL)
            ])

        except Exception as e:
            self.update_ui(lambda: [
                self.progress_label_var.set(f"Error: {e}"),
                self.start_button.config(state=tk.NORMAL)
            ])

    def get_all_shorts_links(self, channel_url):
        # Normalize channel URL to /shorts URL
        if '/@' in channel_url:
            channel_username = channel_url.split('/@')[1].split('/')[0]
            shorts_url = f'https://www.youtube.com/@{channel_username}/shorts'
        else:
            # Remove trailing known suffixes
            for suffix in ['/about', '/community', '/playlist', '/playlists', '/streams', '/featured', '/videos']:
                if channel_url.endswith(suffix):
                    channel_url = channel_url[:-len(suffix)]
            shorts_url = channel_url.rstrip('/') + '/shorts'

        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            # no 'playlistend' to fetch all shorts
            'forceurl': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(shorts_url, download=False)
            entries = result.get('entries', [])
            return [f"https://www.youtube.com/shorts/{entry['id']}" for entry in entries if entry.get('id')]

    def download_video(self, video_url, output_folder, current_index, total_videos):
        def progress_hook(d):
            if d['status'] == 'downloading':
                # percent float is not always present, use downloaded bytes / total_bytes if possible
                pct = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100 if d.get('total_bytes') else 0
                self.update_ui(lambda: self.progress_label_var.set(
                    f"Downloading {current_index}/{total_videos}: {d.get('filename', '')[:30]} {pct:.1f}%"))
            elif d['status'] == 'finished':
                self.update_ui(lambda: self.progress_label_var.set(
                    f"Finished downloading {current_index}/{total_videos}"))

        ydl_opts = {
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            'quiet': True,
            'progress_hooks': [progress_hook],
            'format': 'bestvideo+bestaudio/best',  # Best quality available
            'noplaylist': True,
            'ignoreerrors': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
            except Exception as e:
                self.update_ui(lambda: self.progress_label_var.set(f"Error downloading video {current_index}: {e}"))

        # Update overall progress bar
        self.update_ui(lambda: self.progress_var.set(int((current_index / total_videos) * 100)))

    def update_ui(self, func):
        # Thread-safe UI update using after()
        self.root.after(0, func)


if __name__ == "__main__":
    root = tk.Tk()
    app = ShortsDownloaderApp(root)
    root.mainloop()
