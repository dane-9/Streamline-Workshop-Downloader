![STREAMLINE BANNER](https://github.com/user-attachments/assets/37c2c9d6-a393-4ed2-be74-bfce03b4bef9)

**Streamline** is a user-friendly GUI application **built with PySide6** to help you effortlessly download Steam Workshop mods and collections. Leveraging SteamCMD, this tool simplifies the process of managing multiple Steam accounts, configuring download settings, and queuing mods for efficient downloading with a Realtime Overview of what's happening in, and with the Download Queue interface, it's easy to find mods that have issues or outright failed, with Status Indicators.

## Streamline GUI
![STREAMLINE GUI](https://github.com/user-attachments/assets/43497df5-0e06-49fb-a6a5-a577962e6330)

## Features

- **Steam Account Management**: Add, remove, and manage **multiple Steam accounts** to download mods seamlessly.
- **Mod & Collection Downloading**: Queue individual mods or entire collections from the Steam Workshop. Collections with **900+ Mods Tested.**
- **Batch Processing**: Download multiple mods in configurable batches for optimized performance.
- **Customizable Settings**: Adjust batch sizes, toggle log visibility, and configure other settings to suit your preferences.
- **Detailed GUI with Realtime Overview**: **Monitor downloads as they happen** and troubleshoot issues with a Realtime Overview of what's going on, aided by **Status Indicators for easy troubleshooting**.
- **Queue Management**: Import and export download queues for easy sharing and backup.
- **Automatic SteamCMD Setup**: The application handles the download and setup of SteamCMD. **Passwords are NOT saved** and authentication is exclusively handled by SteamCMD.

*No additional installations or Python dependencies are required as the application is packaged into a standalone executable.*

## Installation

1. **Download the ZIP File**

   Download the latest version of `Streamline.exe` and `AppIDs.txt` bundled together from the [Releases](https://github.com/dane-9/Streamline-Workshop-Downloader/releases) page.

2. **Extract the Files**

   Extract the contents of the downloaded `.zip` file to your desired installation directory. Ensure that the `Streamline.exe` and `AppIDs.txt` are placed in the same folder.


## Usage

1. **Launch the Application**

Double-click on `Streamline.exe` to start the application.

2. **Configure Steam Accounts**

- Click on the **"Configure Steam Accounts"** button.
- In the dialog that appears, click **"Add Steam Account"** to add your Steam username.
- Follow the prompts to authenticate and link your Steam accounts.

3. **Select a Game**

- From the **"Select Game"** dropdown menu, choose the game for which you want to download mods.

4. **Add Mods or Collections**

- **Adding a Mod**:
  - Enter the Workshop Mod URL or ID in the **"Workshop Mod"** input field.
  - Click **"Add to Queue"** to queue the mod for downloading or **"Download"** to download immediately.

- **Adding a Collection**:
  - Enter the Workshop Collection URL or ID in the **"Workshop Collection"** input field.
  - Click **"Add to Queue"** to queue the entire collection for downloading.

5. **Manage Download Queue (Dev branch)**

- **Import Queue**: Load a previously saved download queue from a `.txt` file.
- **Export Queue**: Save the current download queue to a `.txt` file for future use or sharing.

6. **Start Downloading**

- Click the **"Start Download"** button to begin downloading all queued mods.
- Monitor the progress and status of each mod in the **"Download Queue"** section.

7. **View Logs**

- Access detailed logs in the **"Logs"** section to track the download process and troubleshoot any issues.

8. **Open Downloads Folder**

- Once downloads are complete, click **"Open Downloads Folder"** to access your downloaded mods directly.

## Settings

- **Batch Size**: Adjust the number of mods downloaded simultaneously to optimize performance based on your system capabilities.
- **Show Logs**: Toggle the visibility of the logs section to declutter the interface if detailed logs are not needed.

Access the settings by clicking the **"Settings"** button at the top of the application.

## Troubleshooting

- **Invalid App IDs**: Ensure that `AppIDs.txt` is correctly formatted and contains valid game names and App IDs. `GAME,APPID`
- **Download Failures**: Check the logs section for detailed error messages. Common issues include network interruptions or incorrect mod IDs. SteamCMD can be finicky, which is the primary reason this GUI has robust failover.

## Support 

If you encounter any issues or have questions, please open an [issue](https://github.com/dane-9/Streamline-Workshop-Downloader/issues) on the GitHub repository.

## License

This project is licensed under the [GNU Lesser General Public License v3.0 (LGPLv3)](https://www.gnu.org/licenses/lgpl-3.0.html). See the [LICENSE](LICENSE) file for details.


