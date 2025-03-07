![STREAMLINE BANNER](https://github.com/user-attachments/assets/bd9cfce7-dde0-469a-8208-7caa8b9fb91a)

**Streamline** is a user-friendly application **built with PySide6** to help you effortlessly download Steam Workshop mods and collections. Leveraging SteamCMD and SteamWebAPI, this tool simplifies the process of managing multiple Steam accounts, configuring download settings, and queuing mods for efficient downloading.

[![GitHub Release](https://img.shields.io/github/v/release/dane-9/Streamline-Workshop-Downloader.svg?label=Current%20Release&color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge&logo=github)](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) [![GitHub Release Date](https://img.shields.io/github/release-date/dane-9/Streamline-Workshop-Downloader.svg?label=Released&color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge)](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) [![GitHub Downloads](https://img.shields.io/github/downloads/dane-9/Streamline-Workshop-Downloader/total.svg?color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge)](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) [![GitHub Stars](https://img.shields.io/github/stars/dane-9/Streamline-Workshop-Downloader.svg?color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge)](https://github.com/dane-9/Streamline-Workshop-Downloader) [![GitHub License](https://img.shields.io/github/license/dane-9/Streamline-Workshop-Downloader.svg?color=e3dcdc&labelColor=555555&logoColor=ffffff&style=for-the-badge)](https://github.com/dane-9/Streamline-Workshop-Downloader/blob/master/LICENSE)

## User Interface
![STREAMLINE GUI](https://github.com/user-attachments/assets/7fed67c5-2f1e-48cb-a217-d6888b956c15)

## Features

- **Robust Backend** / *<sub>Supports queues with **thousands of mods**.</sub>*
- **Multiple Steam Accounts** / *<sub>Add, remove, and manage **multiple Steam accounts** to download mods.</sub>*
- **Mod & Collection Downloading** / *<sub>Queue individual mods or entire collections from the Steam Workshop.</sub>*
- **Queue Entire Workshop for an AppID** / *<sub>Easily queue all mods from a specific game's Workshop using its AppID. Currently up to **50010 Mods per scrape**.</sub>*
- **Detailed GUI with Realtime Overview** / *<sub>**Monitor downloads as they happen** and troubleshoot issues with a Realtime Overview of what's going on, aided by **Status Indicators for easy troubleshooting**.</sub>*
- **Automatic AppID List Updates** / *<sub>Keep your AppID list up-to-date automatically using Selenium-driven scraping. Scrapes directly from SteamDB.</sub>*
- **Download from Multiple Providers at Once** / *<sub>Simultaneously download mods from **SteamCMD** and **SteamWebAPI** at once and with different AppIDs.</sub>*
- **Automatic SteamCMD Setup** / *<sub>The application handles the download and setup of SteamCMD. **Passwords are NOT saved** and authentication is exclusively handled by SteamCMD.</sub>*
- **Automatic Game Detection** / *<sub>Automatically detects the game associated with a mod to streamline the downloading process.</sub>*
- **Auto-Detect URLs from Clipboard** / *<sub>Automatically detects and processes Steam Workshop URLs copied to your clipboard.</sub>*
- **Import & Export Queue** / *<sub>Import and export download queues for easy sharing and backup.</sub>*
- **Localized Downloads** / *<sub>Downloads mods to a folder next to the application.</sub>*
- **Vertical Mouse Scrolling** / *<sub>Ability to Click mouse-wheel and vertically scroll.</sub>*
- **Queue Reordering** / *<sub>Easily reorder mods in your download queue to prioritize specific downloads.</sub>*
- **Automatic Chromium & Webdriver Setup** / *<sub>Automatically downloads and configures Chromium and WebDriver for web scraping tasks.</sub>*
- **Automatic Virtual Environment Setup** / *<sub>Has a setup that automatically configures a virtual environment for the application. **This is an alternative to using the executable**.</sub>*
- **Batch Processing** / *<sub>Download multiple mods in configurable batches for optimized performance.</sub>*
- **Customizable Settings** / *<sub>Adjust batch sizes, toggle visibility for UI elements, and other settings to suit your preferences.</sub>*

*No additional installations or Python dependencies are required as the application is packaged into a standalone executable.* ***An alternative is using the automatic virtual environment setup***.

## Installation

1. **Download the Executable OR Source Code**

   Download the latest version of `Streamline.exe`  from the [Releases](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) page.
   
   **OR**
   
   Download the `Source Code (zip)` and use the Virtual Environment setup from the [Releases](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) page.

2. **If using the Virtual Environment: Extract the Files**

   Extract the contents of the downloaded `.zip` file to your desired installation directory. And launch the `Run Setup.bat`

## Support 

Before opening an issue, please review the [Documentation](https://github.com/dane-9/Streamline-Workshop-Downloader/wiki/Documentation). 
If you still encounter problems or have questions, feel free to open an [issue](https://github.com/dane-9/Streamline-Workshop-Downloader/issues).

## License

This project is licensed under the [GNU Lesser General Public License v3.0 (LGPLv3)](https://www.gnu.org/licenses/lgpl-3.0.html). See the [LICENSE](LICENSE) file for details.
