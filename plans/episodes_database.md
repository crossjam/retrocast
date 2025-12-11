## Episodes Database Construction

### Overview

The retrocast CLI has the ability to bulk download podcast episodes
using the following command:

```
retrocast download podcast-archiver ...
```

Those files get downloaded into subdirectory of the user specific
application directory $(APP_DIR)/`episode_downloads`

The download command can also take an option `--write-info-json` which
causes the downloader to write JSON metadata beside the download
media. Here’s an example of a listing from such a directory:

```bash
~/Library/Application Support/net.memexponent.retrocast ❯ tree -L 2 episode_downloads/
episode_downloads/
├── Practical AI
│   ├── 2025-11-13 - Autonomous Vehicle Research at Waymo.info.json
│   ├── 2025-11-13 - Autonomous Vehicle Research at Waymo.mp3
│   ├── 2025-11-19 - Beyond note-taking with Fireflies.info.json
│   ├── 2025-11-19 - Beyond note-taking with Fireflies.mp3
│   ├── 2025-11-26 - Chris on AI, autonomous swarming, home automation and Rust!.info.json
│   ├── 2025-11-26 - Chris on AI, autonomous swarming, home automation and Rust!.mp3
│   ├── 2025-12-02 - Technical advances in document understanding.info.json
│   ├── 2025-12-02 - Technical advances in document understanding.mp3
│   ├── 2025-12-10 - The AI engineer skills gap.info.json
│   └── 2025-12-10 - The AI engineer skills gap.mp3
├── Software Engineering Radio - the podcast for professional software developers
│   ├── 2025-11-12 - SE Radio 694- Jennings Anderson and Amy Rose on Overture Maps.info.json
│   ├── 2025-11-12 - SE Radio 694- Jennings Anderson and Amy Rose on Overture Maps.mp3
│   ├── 2025-11-19 - SE Radio 695- Dave Thomas on Building eBooks Infrastructure.info.json
│   ├── 2025-11-19 - SE Radio 695- Dave Thomas on Building eBooks Infrastructure.mp3
│   ├── 2025-11-25 - SE Radio 696- Flavia Saldanha on Data Engineering for AI.info.json
│   ├── 2025-11-25 - SE Radio 696- Flavia Saldanha on Data Engineering for AI.mp3
│   ├── 2025-12-03 - SE Radio 697- Philip Kiely on Multi-Model AI.info.json
│   ├── 2025-12-03 - SE Radio 697- Philip Kiely on Multi-Model AI.mp3
│   ├── 2025-12-09 - SE Radio 698- Srujana Merugu on How to build an LLM App.info.json
│   └── 2025-12-09 - SE Radio 698- Srujana Merugu on How to build an LLM App.mp3
├── Sports Media with Richard Deitsch
│   ├── 2025-12-03 - First Look- ESPN's Malika Andrews and Chiney Ogwumike on the role of agents for sports broadcasters.info.json
│   ├── 2025-12-03 - First Look- ESPN's Malika Andrews and Chiney Ogwumike on the role of agents for sports broadcasters.mp3
│   ├── 2025-12-04 - ESPN's Malika Andrews and Chiney Ogwumike.info.json
│   ├── 2025-12-04 - ESPN's Malika Andrews and Chiney Ogwumike.mp3
│   ├── 2025-12-05 - First Look- Troy Aikman on honesty in NFL broadcasting.info.json
│   ├── 2025-12-05 - First Look- Troy Aikman on honesty in NFL broadcasting.mp3
│   ├── 2025-12-06 - Netflix gets WBD — what's it mean for sports- —  and ESPN and Fox Sports play games with college football press releases.info.json
│   ├── 2025-12-06 - Netflix gets WBD — what's it mean for sports- —  and ESPN and Fox Sports play games with college football press releases.mp3
│   ├── 2025-12-08 - ESPN Monday Night Football analyst Troy Aikman.info.json
│   └── 2025-12-08 - ESPN Monday Night Football analyst Troy Aikman.mp3
└── Talk Python To Me
    ├── 2025-10-27 - #525- NiceGUI Goes 3.0.info.json
    ├── 2025-10-27 - #525- NiceGUI Goes 3.0.mp3
    ├── 2025-11-01 - #526- Building Data Science with Foundation LLM Models.info.json
    ├── 2025-11-01 - #526- Building Data Science with Foundation LLM Models.mp3
    ├── 2025-11-10 - #527- MCP Servers for Python Devs.info.json
    ├── 2025-11-10 - #527- MCP Servers for Python Devs.mp3
    ├── 2025-11-30 - #528- Python apps with LLM building blocks.info.json
    ├── 2025-11-30 - #528- Python apps with LLM building blocks.mp3
    ├── 2025-12-03 - #529- Computer Science from Scratch.info.json
    └── 2025-12-03 - #529- Computer Science from Scratch.mp3

5 directories, 40 files
```

`retrocast` also keeps its own sqlite database in `retrocast.db`.

### Requirements

- Update `retrocast.cli_attach_podcast_archiver_passthroughs` so that
  the default for `--write-info-json` true is the default.
  
- Define a data model for the `retrocast.db` intended to ingest the
  resolved path names for the podcasts and their JSON metadata
  
- Keep the JSON information in a sqlite JSON column

- Track the pathname and update times for the episode media file
  (e.g. "foo.mp3")
  
- Add text indexes for searching where it seems like a good idea
  
- Design a new package that includes code to initialize this data model
  
- Add code to the package to update those tables by scanning the
  `episodes_download` folder for new information
  
- Implement a new `db` subgroup for the `download` group 

- Implement a new `download db init` subcommand that initializes the
  new episodes information schemas using the new package
  
- Implement a new `download db update` subcommand that updates the
  episodes download information using the new package
