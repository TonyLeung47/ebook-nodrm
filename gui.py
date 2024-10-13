import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ebook import Ebook
from setting import load_setting


class Application(tk.Frame):
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.master = master
        self.pack(fill=tk.BOTH, expand=True)

        self.only_image = tk.BooleanVar(value=False)
        self.book = Ebook()
        self.create_widgets()

    def create_widgets(self) -> None:
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 12))
        style.configure("TCheckbutton", font=("Helvetica", 12))

        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(frame, selectmode=tk.EXTENDED, font=("Helvetica", 12))
        self.listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        for item in self.book.books:
            self.listbox.insert(tk.END, item.get_title() or "Unknown")

        path_frame = ttk.Frame(self)
        path_frame.pack(side=tk.TOP, fill=tk.X, padx=10)

        self.only_image_check_button = ttk.Checkbutton(path_frame, text="Extract Only Image", variable=self.only_image)
        self.only_image_check_button.pack(side=tk.TOP, anchor=tk.CENTER)

        self.folder_path_var = tk.StringVar(value=str(load_setting().default_folder))
        self.folder_path_entry = ttk.Entry(path_frame, textvariable=self.folder_path_var, font=("Helvetica", 12))
        self.folder_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.browse_button = ttk.Button(path_frame, text="Browse", command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT, padx=10, pady=5)

        self.get_selected_button = ttk.Button(
            self,
            text="Decrypt",
            command=self.decrypt,
        )
        self.get_selected_button.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

    def browse_folder(self) -> None:
        folder_path = filedialog.askdirectory()
        self.folder_path_var.set(folder_path)

    def decrypt(self) -> None:
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return

        folder = self.folder_path_var.get()
        if self.only_image.get():
            self.book.decrypt_images(folder, selected_indices)
        else:
            self.book.decrypt(folder, selected_indices)
        messagebox.showinfo("Info", "Decrypt is done!")


def main():
    win = tk.Tk("Ebook Decrypter")
    win.geometry("600x400")
    app = Application(master=win)
    app.mainloop()


if __name__ == "__main__":
    main()
