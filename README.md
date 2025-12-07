<!-- NOTE: Fork Information -->
> This repository is a maintained fork of the original Fireshare project. Most users should consider using or contributing to the upstream project instead: https://github.com/ShaneIsrael/fireshare. This fork may diverge for experimentation and additional features.

<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/sim2kid/fireshare">
    <img src="app/client/src/assets/logo.png" alt="Logo" width="120" height="160">
  </a>

  <h1 align="center">Fireshare</h1>

  <p align="center">
    Share your game clips, videos, or other media via unique links.
    <br />
    <br />
    <a href="https://github.com/sim2kid/fireshare/actions">
      <img alt="Docker Build" src="https://github.com/sim2kid/fireshare/actions/workflows/docker-publish-main.yml/badge.svg" />
    </a>
    <a href="https://hub.docker.com/r/sim2kid/fireshare">
      <img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/sim2kid/fireshare?label=docker%20pulls">
    </a>
    <a href="https://hub.docker.com/r/sim2kid/fireshare/tags?page=1&ordering=last_updated">
      <img alt="GitHub tag (latest SemVer)" src="https://img.shields.io/github/v/tag/sim2kid/fireshare?label=version">
    </a>
    <a href="https://github.com/sim2kid/fireshare/stargazers">
      <img alt="GitHub stars" src="https://img.shields.io/github/stars/sim2kid/fireshare">
    </a>
    <br />
    <br />
    <a href="https://v.fireshare.net">Live Demo</a>
    ·
    <a href="https://github.com/sim2kid/fireshare/issues">Report a Bug</a>
    </p>
</p>

<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li><a href="#changelog">Changelog</a></li>
    <li>
      <a href="#installation">Installation</a>
      <ul>
        <li><a href="#configurable-settings">Configurable Settings</a></li>
      </ul>
    </li>
    <li>
      <a href="#local-development">Local Development</a>
      <ul>
        <li><a href="#setup">Setup</a></li>
        <li><a href="#docker-based-dev-optional">Docker-based Dev (optional)</a></li>
      </ul>
    </li>
    <li><a href="#contributing">Contributing</a></li>
    <li>
      <a href="#frequently-asked-questions">FAQ / Troubleshooting</a>
      <ul>
        <li><a href="#playback-issues">Playback Issues</a></li>
      </ul>
    </li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

# About The Project

I create a lot of game clips with tools such as Nvidia's Shadowplay, many of these clips are short 15-30 second clips that I want to share with my friends but do not want to spend the time uploading them to YouTube, waiting for YouTube to process the video and then finally being able to send them a link.

I thought that there had to be a simple solution that allowed me the ability to self host my clips and share them with my friends through some generated link? Unfortunately nothing I found was quite what I was looking for. So with the help of a friend we quickly built Fireshare to do just that.

The goal of Fireshare is to provide a very simple and easy way for you to share any videos you have through a unique link. All you have to do is put your videos in a folder and Fireshare will take care of the rest.

![login-screen]

<h2 align="center">The Dashboard</h2>
<p align="center">Here you can see all of your videos and edit their details such as title, description and whether or not you want them to show up on the public feed.</p>

![card-view]

<p align="center">Maybe card view isn't your style? Fireshare also supports a list style view as well.</p>

![list-view]

<h2 align="center">Foldered Sorting</h2>
<p align="center">Fireshare will use the top most directory that your videos are in as an easy and simple way for you to organize your videos into categories of your choosing.</p>

![folders]

<h2 align="center">Uploading</h2>
<p align="center">Allow your community or the public the ability to upload videos. Of course, this feature can be disabled or limited to only administrator access</p>

![uploading]

<h2 align="center">Edit Video Details</h2>
<p align="center">Access a basic modal for editing the title and description of videos by clicking on the "pencil" icon.</p>

![edit-details]

<h2 align="center">Video Preview Modal</h2>
<p align="center">Videos opened when on the public feed or admin dashboard show up in a modal. This modal gives you direct link and timestamped link sharing buttons as well as the ability to "shuffle" randomly to another video. As an admin, you can also edit the details of the video from this modal. </p>

![preview-modal]

<h2 align="center">The Watch Page</h2>
<p align="center">This is what people will see when given a Fireshare link. </p>

![watch-page]

<h2 align="center">Mobile Support</h2>
<p align="center">
Prefer to browse on your mobile device? No problem. Fireshare has you covered.
</p>

<p align="center"><img src=".github/images/mobile-view.png" width="400px"/></p>

<h2 align="center">Open Graph Support</h2>
<p align="center">
Direct links copied from the link copy buttons in Fireshare will allow websites and messaging apps to read the open graph data and show title, description and video thumbnails in your posts.
</p>
<p align="center">
<img src=".github/images/ogg-data.png" alt="Logo">
</p>

<h2 align="center">LDAP Authentication Support</h2>
<p align="center">
Connect Fireshare to a central user directory and keep user access organised.
</p>

### Built With

- [React](https://reactjs.org/)
- [Python](https://www.python.org/)
- [Material UI](https://mui.com/)

<!--- CHANGE LOG --->

# Changelog

## v1.2.13
```
  Added a catch for finding corrupt or malformed files when initiating a scan
```

<!-- GETTING STARTED -->

# Installation

Fireshare is meant to run within a Docker environment. While we reccommend using something like Docker Compose it is not required and can run with a simple `docker run` command.

Fireshare needs 3 volume mounts.

1. **/data** - The directory used by fireshare to hold its internal database
2. **/processed** - The directory used to hold metadata created by fireshare in relation to your videos (posters, metadata info)
3. **/videos** - The directory fireshare will watch and scan for any videos.

If you have all of your game clips stored in a folder **my_game_clips** then in your docker compose file (or docker run command) you will need to volume mount that folder to the **/videos** folder that fireshare watches.

### Docker Compose

If you have docker compose installed, at the root of this project you can simply run this command.

> **make sure you edit the docker-compose.yml** file with your volume locations and admin password.

```
docker-compose up -d
```

### Docker

```
docker run --name fireshare -v $(pwd)/fireshare:/data:rw -v $(pwd)/fireshare_processed:/processed:rw -v /path/to/my_game_clips:/videos:rw -p 8080:80 -e ADMIN_PASSWORD=your-admin-password -d sim2kid/fireshare:latest
```

Once running, navigate to `localhost:8080` in your browser.

### Configurable Settings

See the Fireshare Configuration Wiki: <a href="https://github.com/ShaneIsrael/fireshare/wiki/Fireshare-Configurables">Link</a>  
For LDAP configuration, see [LDAP.md](./LDAP.md)

### Video Transcoding (Optional)

Fireshare supports automatic transcoding of videos to create 720p and 1080p quality variants using the AV1 codec for better compression. This feature is **disabled by default** and must be explicitly enabled.

**Benefits:**
- Smaller file sizes with AV1 compression (up to 50% smaller than H.264)
- Better streaming performance for users with limited bandwidth
- Quality selection in the video player

**Requirements:**
- FFmpeg with NVENC, libaom-av1, VP9, and codec support (included in the Docker image)
- CPU transcoding works out of the box

**GPU Transcoding:**
The Docker image includes FFmpeg compiled with NVENC support for GPU-accelerated transcoding. To use GPU transcoding:
  - NVIDIA GPU with NVENC support (GTX 1050+ / Pascal or newer)
  - NVIDIA drivers installed on the host system
  - NVIDIA Container Toolkit on the host system
  - See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
  
Benefits of GPU transcoding:
- 5-10x faster than CPU encoding
- Lower power consumption
- Frees up CPU for other tasks

**Environment Variables:**
```yaml
# Enable automatic transcoding during video scans (default: false)
ENABLE_TRANSCODING=true

# Enable GPU acceleration for transcoding using NVENC (default: false)
# Requires nvidia-docker runtime
TRANSCODE_GPU=true
```

**Docker Compose GPU Setup:**
```yaml
services:
  fireshare:
    # ... other configuration ...
    environment:
      - ENABLE_TRANSCODING=true
      - TRANSCODE_GPU=true
      - NVIDIA_DRIVER_CAPABILITIES=all
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Manual Transcoding:**

If you have existing videos that were scanned before enabling transcoding, you can manually transcode them:

```bash
# Transcode all videos in your library
docker exec -it fireshare fireshare transcode-videos

# Transcode a specific video by its ID
docker exec -it fireshare fireshare transcode-videos --video VIDEO_ID

# Regenerate transcoded versions (overwrites existing)
docker exec -it fireshare fireshare transcode-videos --regenerate
```

**Important Notes for Existing Videos:**
- The `transcode-videos` command only processes videos when `ENABLE_TRANSCODING=true` is set
- Transcoding happens in the background and can take significant time depending on:
  - Number and size of videos
  - CPU/GPU performance
  - Whether GPU acceleration is enabled
- Progress is logged in the container logs: `docker logs -f fireshare`
- Only videos larger than the target resolution will be transcoded (e.g., 4K videos will get 1080p and 720p variants)
- Original files are never modified or deleted
- You can check if a video has been transcoded by looking at the quality selector in the player
- To find a video's ID, check the URL when viewing it (e.g., `/w/VIDEO_ID`)

**Workflow for Upgrading Existing Installations:**

1. **Pull the latest image** (if using Docker):
   ```bash
   docker pull sim2kid/fireshare:latest
   ```
   
   Or if using docker-compose:
   ```bash
   docker-compose pull
   ```

2. **Stop and remove the old container**:
   ```bash
   docker stop fireshare && docker rm fireshare
   ```
   
   Or with docker-compose:
   ```bash
   docker-compose down
   ```

3. **Enable transcoding** by adding environment variables to your docker-compose.yml or docker run command:
   ```yaml
   ENABLE_TRANSCODING=true
   TRANSCODE_GPU=true  # Optional, for GPU acceleration
   ```

4. **Start the container** - Database migrations will run automatically:
   ```bash
   docker-compose up -d
   ```
   
   Or with docker run:
   ```bash
   docker run --name fireshare -v $(pwd)/fireshare:/data:rw -v $(pwd)/fireshare_processed:/processed:rw -v /path/to/videos:/videos:rw -p 8080:80 -e ADMIN_PASSWORD=your-password -e ENABLE_TRANSCODING=true -d sim2kid/fireshare:latest
   ```
   
   **Note:** The database migration to add transcoding columns runs automatically on container startup via `flask db upgrade` in the entrypoint.

5. **Verify the migration ran successfully**:
   ```bash
   docker logs fireshare | grep "Running upgrade"
   ```
   You should see: `INFO  [alembic.runtime.migration] Running upgrade a4503f708aee -> b7e8541487dc, add transcoding support`

6. **Transcode existing videos** using one of these approaches:

   **Option A: Transcode everything at once (recommended for small libraries)**
   ```bash
   docker exec -it fireshare fireshare transcode-videos
   ```

   **Option B: Transcode videos gradually (recommended for large libraries)**
   ```bash
   # Get a list of video IDs from your admin dashboard
   # Then transcode them one at a time or in batches
   docker exec -it fireshare fireshare transcode-videos --video VIDEO_ID_1
   docker exec -it fireshare fireshare transcode-videos --video VIDEO_ID_2
   # ... etc
   ```

4. **Future videos** will be automatically transcoded during the scan process (every 5 minutes by default)

**Monitoring Progress:**
```bash
# Watch transcoding logs in real-time
docker logs -f fireshare

# Check if transcoding is running
docker exec -it fireshare ps aux | grep ffmpeg
```

**GPU Setup (Optional but Recommended):**

To use GPU acceleration, you need to:

1. Install NVIDIA drivers on your host system
2. Install NVIDIA Container Toolkit:
   ```bash
   # Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

3. Verify GPU is available on host:
   ```bash
   docker run --rm --runtime=nvidia --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
   ```
   
   **Note:** The Fireshare container doesn't include `nvidia-smi`. To verify GPU access in Fireshare, use:
   ```bash
   docker exec -it fireshare ffmpeg -encoders 2>/dev/null | grep nvenc
   ```

4. Update your docker-compose.yml with GPU configuration (see example above)

**Unraid GPU Setup:**

For Unraid users who want to pass their NVIDIA GPU to the Fireshare container:

1. **Install NVIDIA Driver Plugin:**
   - In Unraid, go to Apps/Community Applications
   - Search for "NVIDIA Driver" and install the plugin
   - The plugin will automatically install NVIDIA drivers on boot

2. **Configure Fireshare Container in Unraid:**
   - Edit the Fireshare container in Unraid's Docker tab
   - Add the following environment variables:
     ```
     ENABLE_TRANSCODING=true
     TRANSCODE_GPU=true
     NVIDIA_DRIVER_CAPABILITIES=all
     ```
   
3. **Enable GPU Passthrough:**
   - In the container settings, scroll to "Extra Parameters"
   - Add: `--gpus=all`
   - **Important:** Use `--gpus=all` instead of `--runtime=nvidia` for Unraid

4. **Verify GPU Access:**
   
   The Fireshare container doesn't include `nvidia-smi`, but you can verify GPU access in these ways:
   
   **Method 1: Check FFmpeg GPU encoders (Recommended)**
   ```bash
   docker exec -it fireshare ffmpeg -encoders 2>/dev/null | grep nvenc
   ```
   You should see output like:
   ```
   V..... h264_nvenc           NVIDIA NVENC H.264 encoder
   V..... hevc_nvenc           NVIDIA NVENC hevc encoder
   ```
   
   **Method 2: Monitor transcoding logs**
   - Enable transcoding with `TRANSCODE_GPU=true`
   - Check the logs while a video is transcoding:
     ```bash
     docker logs -f fireshare
     ```
   - Look for "Transcoding video to 720p using GPU H.264 (NVENC)" messages
   
   **Method 3: Verify GPU usage (from Unraid host)**
   - While transcoding is running, check GPU usage:
     ```bash
     nvidia-smi
     ```
   - You should see FFmpeg processes using the GPU with video encoder/decoder utilization

5. **Advanced Configuration (Optional):**
   - If you want to limit to specific GPUs, use:
     ```
     --gpus='"device=0"'
     ```
   - For multiple specific GPUs:
     ```
     --gpus='"device=0,1"'
     ```

**Notes:**
- Transcoding only creates quality variants for videos larger than the target resolution
- Original files are always preserved
- The video player will automatically show a quality selector when transcoded versions are available
- FFmpeg is compiled with NVENC support for GPU-accelerated transcoding
- GPU transcoding is 5-10x faster than CPU transcoding

**Transcoding Fallback Chain:**

**GPU Mode** (`TRANSCODE_GPU=true`):
1. **AV1 with GPU (av1_nvenc)** - Best compression, RTX 40 series or newer (Ada Lovelace)
2. **H.264 with GPU (h264_nvenc)** - Fast and widely supported, GTX 1050+ (Pascal or newer)
3. **AV1 with CPU (libaom-av1)** - Excellent compression if GPU encoding fails
4. **H.264 with CPU (libx264)** - Final fallback, universally compatible

**CPU Mode** (`TRANSCODE_GPU=false` or GPU unavailable):
1. **AV1 with CPU (libaom-av1)** - Best compression, slower
2. **H.264 with CPU (libx264)** - Fallback if AV1 fails

The system automatically tries AV1 NVENC first on all GPUs, then falls back to H.264 NVENC for older GPUs that don't support AV1 hardware encoding.

# Local Development

If you would like to run Fireshare via the source code in order to contribute you will need to have npm, Node.js and Python installed. I reccommend installing Node.js with NVM so that you can easily switch between Node versions.

### Setup

1. Have Python3, NodeJS and NPM installed.
2. Clone the repo
   ```sh
   $ git clone https://github.com/sim2kid/fireshare.git
   ```
3. At the project root
   ```sh
   $ ./run_local.sh
   ```
4. In a new terminal, navigate to `app/client` and run the following commands.
   ```sh
   $ npm i && npm start
   ```
5. In your browser, navigate to `localhost:3000` and login with admin/admin

### Docker-based Dev (optional)

For a quick local development environment that matches the containerized runtime, you can use the provided docker-compose.dev.yml:

```sh
docker compose -f docker-compose.dev.yml up -d
```

Then open http://localhost:8080 and log in with the default admin credentials defined in the compose file (change them for your environment).

<!-- CONTRIBUTING -->

# Contributing

If this project is at all interesting to you please feel free to contribute or create suggestions if you have them. Please note that creating a pull request does not guarantee it will be accepted into the project. Outside of obvious bug fixes it may be best to consult with us before starting work on any additions you'd like to make.

[For questions or feature requests please create an issue with an appropriate label here](https://github.com/sim2kid/fireshare/issues/new)

1. Fork the Project
2. Add upstream (`git remote add upstream https://github.com/sim2kid/fireshare.git`)
3. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
4. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
5. Rebase with upstream (`git rebase upstream/main`)
6. Fix any merge conflicts you may have
7. Push to the Branch (`git push origin feature/AmazingFeature`)
8. Open a Pull Request against the **develop** branch

**UPDATE YOUR BRANCH** We will not fix merge conflicts for you, if you make a pull request and it states there are merge conflicts please see steps 4 and 5 from the above.

### Updating the Fireshare Database

If you need to update the database or add a new table / column first make your changes to the `app/server/fireshare/models.py` file then at the root of the project run `flask db migrate -m "name of migration"` a new migration will be made with your changes. Go to that file and double check that everything is correct. You may need to manually edit this migration.

# Frequently Asked Questions

### Playback Issues

If you are experiencing playback issues, here are the most common causes and how the new streaming pipeline addresses them:

1. Browser compatibility (Firefox vs. others)

   This fork introduces a browser‑compatible MP4 streaming path with dynamic codec selection and on‑the‑fly transcoding, targeting reliable playback in Firefox while preserving direct‑play paths for Chrome/Edge/Safari when possible. The `/api/stream` endpoint negotiates codecs and may transcode on demand; when the source is already compatible it will stream without unnecessary work.

   Tip: The player can now issue a `HEAD` request to `/api/stream` to quickly probe media headers; the server responds with `Content-Duration` to improve startup behavior and UI accuracy.

2. File size and bandwidth

   Large source files still require sufficient server upload bandwidth and client download bandwidth. Transcoding to a more efficient or lower‑bitrate variant can help. The system avoids redundant work via caching and per‑output locking, so once a variant exists subsequent plays should start faster.

3. Unsupported file types/containers

   When a source container/codec is not natively playable in the requesting browser, the server will select a compatible output and transcode on the fly (copying audio/video when safe). This reduces the need to pre‑transcode your entire library. If a particular codec path failed previously for a given source, Fireshare will de‑prioritize that path for future attempts to improve reliability.

4. Upload issues behind reverse proxies

   If you place Fireshare behind Nginx or another reverse proxy, ensure upload size and timeouts are increased appropriately. For Nginx, for example:

   ```
   client_max_body_size 0;
   proxy_read_timeout 999999s;
   ```

   With `client_max_body_size` set to `0` any size upload is allowed. Increase timeouts to prevent long uploads from being cut off. Adjust similarly for non‑Nginx proxies.

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[contributors-shield]: https://img.shields.io/github/contributors/sim2kid/fireshare.svg?style=for-the-badge
[contributors-url]: https://github.com/sim2kid/fireshare/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/sim2kid/fireshare.svg?style=for-the-badge
[forks-url]: https://github.com/sim2kid/fireshare/network/members
[stars-shield]: https://img.shields.io/github/stars/sim2kid/fireshare.svg?style=for-the-badge
[stars-url]: https://github.com/sim2kid/fireshare/stargazers
[issues-shield]: https://img.shields.io/github/issues/sim2kid/fireshare.svg?style=for-the-badge
[issues-url]: https://github.com/sim2kid/fireshare/issues
[card-view]: .github/images/card-view.png
[edit-details]: .github/images/edit-details.png
[folders]: .github/images/folders.png
[login-screen]: .github/images/login-screen.png
[list-view]: .github/images/list-view.png
[preview-modal]: .github/images/preview-modal.png
[watch-page]: .github/images/watch-page.png
[ogg-data]: .github/images/ogg-data.png
[mobile-view]: .github/images/mobile-view.png
[uploading]: .github/images/uploading.png
