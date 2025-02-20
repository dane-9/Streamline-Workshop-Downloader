![STREAMLINE BANNER](https://github.com/user-attachments/assets/37c2c9d6-a393-4ed2-be74-bfce03b4bef9)

**Streamline** is a user-friendly GUI application **built with PySide6** to help you effortlessly download Steam Workshop mods and collections. Leveraging SteamCMD and SteamWebAPI, this tool simplifies the process of managing multiple Steam accounts, configuring download settings, and queuing mods for efficient downloading. With a Realtime Overview of what's happening in the Download Queue interface, it's easy to find mods that have issues or outright failed, thanks to Status Indicators.

## Streamline GUI
![STREAMLINE GUI](https://github.com/user-attachments/assets/307ac847-2cc3-42fd-92b8-08e91e681bae)


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
- **Mods in Queue Counter** / *<sub>Visual counter displaying the number of mods currently in the download queue.</sub>*
- **Localized Downloads** / *<sub>Downloads mods to a folder next to the application.</sub>*
- **Vertical Mouse Scrolling** / *<sub>Ability to Click mouse-wheel and vertically scroll.</sub>*
- **Queue Reordering** / *<sub>Easily reorder mods in your download queue to prioritize specific downloads.</sub>*
- **Automatic Chromium & Webdriver Setup** / *<sub>Automatically downloads and configures Chromium and WebDriver for web scraping tasks.</sub>*
- **Automatic Virtual Environment Setup** / *<sub>Has a setup that automatically configures a virtual environment for the application. **This is an alternative to using the executable**.</sub>*
- **Option to Keep Downloads in Queue** / *<sub>Choose to retain downloaded mods in the queue for future reference or actions.</sub>*
- **Batch Processing** / *<sub>Download multiple mods in configurable batches for optimized performance.</sub>*
- **Customizable Settings** / *<sub>Adjust batch sizes, toggle visibility for UI elements, and other settings to suit your preferences.</sub>*

*No additional installations or Python dependencies are required as the application is packaged into a standalone executable.* ***An alternative is using the automatic virtual environment setup***.

## Installation

1. **Download the Executable OR Source Code**

   Download the latest version of `Streamline.exe`  from the [Releases](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) page.
   
   **OR**
   
   Download the `Source Code (zip)` and use the Virtual Environment setup from the [Releases](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) page.

2. **Extract the Files**

   Extract the contents of the downloaded `.zip` file to your desired installation directory. And launch the `Run Setup.bat`



## Usage

1. **Launch the Application**

   Double-click on `Streamline.exe` or `Streamline.bat` to start the application.

2. **Configure Steam Accounts**

   - Click on the **"Configure Steam Accounts"** button.
   - In the dialog that appears, click **"Add Steam Account"** to add your Steam username.
   - Follow the prompts to authenticate and link your Steam accounts.

3. **Add Mods or Collections**

   - **Adding a Mod**:
     - Enter the Workshop Mod URL or ID in the **"Workshop Mod"** input field.
     - Click **"Add to Queue"** to queue the mod for downloading or **"Download"** to download immediately.

   - **Adding a Collection**:
     - Enter the Workshop Collection URL or ID in the **"Workshop Collection"** input field.
     - Click **"Add to Queue"** to queue the entire collection for downloading.

4. **Manage Download Queue**
   
   - **Import Queue**: Load a previously saved download queue from a `.txt` file.
   - **Export Queue**: Save the current download queue to a `.txt` file for future use or sharing.

5. **Start Downloading**

   - Click the **"Start Download"** button to begin downloading all queued mods.
   - Monitor the progress and status of each mod in the **"Download Queue"** section.

6. **View Logs**

   - Access detailed logs in the **"Logs"** section to track the download process and troubleshoot any issues.

7. **Open Downloads Folder**

   - Once downloads are complete, click **"Open Downloads Folder"** to access your downloaded mods directly.

## Settings

- **Batch Size**: Adjust the number of mods downloaded simultaneously to optimize performance based on your system capabilities.
- **Show Logs**: Toggle the visibility of the logs section to declutter the interface if detailed logs are not needed.
- **Show Download Provider**: Toggle the visibility of the download provider column in the queue.
- **Show Queue Entire Workshop Button**: Toggle the visibility of the button to queue entire workshops.
- **Auto-Detect URLs from Clipboard**: Enable or disable automatic detection of Workshop URLs copied to the clipboard.
- **Auto-Add Detected URLs to Queue**: Automatically add detected Workshop URLs to the download queue.
- **Keep Downloaded Mods in Queue**: Choose whether to retain downloaded mods in the queue after completion.

Access the settings by clicking the **"Settings"** button at the top of the application.

## Troubleshooting

- **Download Failures**: Check the logs section for detailed error messages. Common issues include network interruptions or incorrect mod IDs. SteamCMD can be finicky, which is the primary reason this GUI has robust failover mechanisms. Most effective solution is to remove the entire steamcmd folder and restart the application.
- **SteamCMD Issues**: Ensure SteamCMD was properly installed. Re-run the application to trigger automatic setup if necessary.
- **Selenium and WebDriver Errors**: Verify that Chromium and WebDriver are correctly set up. The application handles automatic setup, but manual intervention may be required in rare cases.

## Support 

If you encounter any issues or have questions, please open an [issue](https://github.com/dane-9/Streamline-Workshop-Downloader/issues) on the GitHub repository.

## License

This project is licensed under the [GNU Lesser General Public License v3.0 (LGPLv3)](https://www.gnu.org/licenses/lgpl-3.0.html). See the [LICENSE](LICENSE) file for details.
