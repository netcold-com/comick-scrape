# comick-scrape

Convert a Proxmox LXC into a comick.io **vibe-coded** archive server.

---

## About

This project was tested in a **Proxmox LXC running Debian 12.7**.

It’s a **side project** created as a backup solution in case **comick.io goes down**.

I’m **not a professional programmer**, so please don’t expect polished code or perfect software.  
Use at your own risk and feel free to improve or contribute!

---

## Installation

Inside a Proxmox LXC running debian, run the following command to install everything:

```bash
curl -sSL https://raw.githubusercontent.com/netcold-com/comick-scrape/refs/heads/main/main.sh | sudo bash
```
---

## Usage & Notes

- The file `update-chapters.txt` is located in `/var/www/html/manhwa/`.

- You can **edit `update-chapters.txt` to add or update comic links**.

- You get the option to install **Apache** to serve the files for browsing

- You also get the option to create systemd scripts to **automatically update every Sunday at 00:00 UTC**.

- If you need to **run the scripts manually**, you can use these commands:

    ```bash
    xvfb-run -a python3 /var/www/html/manhwa/fetchUrls.py
    xvfb-run -a python3 /var/www/html/manhwa/downloadChapters.py
    ```

- Make sure to run the manual commands as the `manhwa` user or with proper permissions

- Password of user `manhwa` is also `manhwa`, I **highly recommend** changing it

---

## Contributing

Feel free to fork and submit pull requests if you want to improve the project! (I'm not super active, I might not see it)

---

## Roadmap / Changes I'd like to make

- Docker Container support
- Clean up the scripts (they're vibe-coded after all)
- Better error handling 
- Optimize download speed (multi-thread?)
- Language options
