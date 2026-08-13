![STREAMLINE BANNER](https://github.com/user-attachments/assets/bd9cfce7-dde0-469a-8208-7caa8b9fb91a)

**Streamline** is a modern, cross-platform Steam Workshop downloader **built with pywebview**. It lets you queue, manage, and download individual Workshop items, collections, or an entire game's Workshop through an intuitive interface powered by SteamCMD and SteamWebAPI.

[![GitHub Release](https://img.shields.io/github/v/release/dane-9/Streamline-Workshop-Downloader.svg?label=Current%20Release&color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge&logo=github)](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) [![GitHub Release Date](https://img.shields.io/github/release-date/dane-9/Streamline-Workshop-Downloader.svg?label=Version%20Released&color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge)](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) [![GitHub Downloads](https://img.shields.io/github/downloads/dane-9/Streamline-Workshop-Downloader/total.svg?color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge)](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) [![GitHub Stars](https://img.shields.io/github/stars/dane-9/Streamline-Workshop-Downloader.svg?color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge)](https://github.com/dane-9/Streamline-Workshop-Downloader)

## User Interface
<img src="https://i.imgur.com/sn49Zi2.png" alt="gui" width="600"/>

## Features
| Feature | Description |
|---|---|
| **Virtual-Scrolled Queue** | *<sub>Handles **thousands of mods** with no lag. Includes marquee selection, bulk actions, drag reordering, drag-and-drop importing, status filtering, and animated status badges.</sub>* |
| **Command Palette** | *<sub>A searchable launcher (`Ctrl+K` or double-tap `Shift`) that gives you fast access to **every action** in the app.</sub>* |
| **Interactive SteamCMD Terminal** | *<sub>Authenticate accounts directly inside Streamline. Streams SteamCMD output in real time and lets you enter **Steam Guard codes** without leaving the app. Password input is visible as you type for convenience (unlike SteamCMD's hidden input).<br>**Passwords are NOT saved**; authentication is handled exclusively by SteamCMD.</sub>* |
| **Realtime Log Overview** | *<sub>Logs are organized into collapsible operation groups with **color-coded state badges** (`RUN` / `DONE` / `WARN` / `ERROR` / `STOP`), in-place progress updates, and category filtering.</sub>* |
| **Multiple Steam Accounts** | *<sub>Add, remove, re-authenticate, and **drag-reorder** multiple Steam accounts. Avatars are fetched and displayed automatically.</sub>* |
| **Mod & Collection Downloading** | *<sub>Queue individual mods, entire collections, or an **entire game's Workshop** (up to 50,010 mods per scrape).</sub>* |
| **Download from Multiple Providers** | *<sub>Simultaneously download mods from **SteamCMD** and **SteamWebAPI** at once and with different AppIDs.</sub>* |
| **Automatic SteamCMD Setup** | *<sub>Streamline handles downloading and initializing SteamCMD automatically.</sub>* |
| **Automatic AppID Updates** | *<sub>Keep your AppID list current by scraping directly from SteamDB using **Botasaurus**. Supports headless and visible browser modes.</sub>* |
| **Automatic Game Detection** | *<sub>Automatically detects the game associated with a mod when queueing.</sub>* |
| **Clipboard URL Detection** | *<sub>Detects Steam Workshop URLs copied to your clipboard and optionally adds them to the queue automatically.</sub>* |
| **Import & Export Queue** | *<sub>Save and load download queues for sharing or backup.</sub>* |
| **Batch Processing** | *<sub>Download mods in configurable batches for optimized performance.</sub>* |
| **Customizable Settings** | *<sub>Adjust themes, batch sizes, folder naming, provider defaults, visibility toggles, and startup behavior. Includes the new grid-backed **Default** theme.</sub>* |
| **Custom Frameless Window** | *<sub>Fully frameless window with a custom title bar, native resizing, persistent window size, and improved Wayland behavior.</sub>* |

## Installation

### Option A: Packaged Release

#### Windows

1. Download `Streamline-Windows.zip` from the latest entry on the [Releases](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) page
2. Extract the entire ZIP to a folder
3. Launch `Streamline.exe` from the extracted folder

#### Linux

1. Download `Streamline.AppImage` from the latest entry on the [Releases](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) page
2. Place it in its own folder
3. Make it executable:
   ```bash
   chmod +x Streamline.AppImage
   ```
4. Launch it:
   ```bash
   ./Streamline.AppImage
   ```
   Or double-click the AppImage after making it executable.

### Option B: Run from Source (in a Virtual Environment)

If you prefer to run from source code:

1. Clone the repository:
   ```bash
   git clone https://github.com/dane-9/Streamline-Workshop-Downloader.git
   ```
2. Navigate to the directory:
   ```bash
   cd Streamline-Workshop-Downloader
   ```
3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r Files/requirements.txt
   ```
   Linux also requires the Qt backend:
   ```bash
   pip install PySide6
   ```
5. Run Streamline:
   ```bash
   python downloader.py
   ```

## Support

Before opening an issue, please review the [Documentation](https://github.com/dane-9/Streamline-Workshop-Downloader/wiki/Documentation).
If you still encounter problems or have questions, feel free to open an [issue](https://github.com/dane-9/Streamline-Workshop-Downloader/issues).

## License

This project is licensed under the [GNU Lesser General Public License v3.0 (LGPLv3)](https://www.gnu.org/licenses/lgpl-3.0.html). See the [LICENSE](LICENSE) file for details.
