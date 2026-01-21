# Aria2 Crawler Implementation Plan

## Overview

Create a new `crawl` CLI subgroup with an `aria` subcommand that uses
the embedded aria2c subprocess (from `ariafetcher.py`) to download
files from URLs provided via file or stdin.

## Command Interface

### Usage Examples

```bash
# Read URLs from a file
retrocast crawl aria urls.txt

# Read URLs from stdin
echo "https://example.com/file.mp3" | retrocast crawl aria -
cat urls.txt | retrocast crawl aria -

# With options
retrocast crawl aria urls.txt -d ./downloads -j 10 -v
```

### Command Signature

```
retrocast crawl aria [OPTIONS] [FILENAME]
```

### Arguments

- `FILENAME`: Path to file containing URLs (one per line), or `-` for stdin. If omitted, defaults to stdin.

### Options

- `-d, --directory PATH`: Download directory (default: current working directory)
- `-j, --max-concurrent INTEGER`: Maximum concurrent downloads (default: 5)
- `-v, --verbose`: Show verbose output including aria2c logs
- `--secret TEXT`: Optional RPC secret for aria2c (for security)

## Architecture

### Module Structure

```
src/retrocast/
├── cli.py                    # Add 'crawl' subgroup here
├── logging_config.py         # NEW: Loguru logging configuration
├── crawl_commands.py         # NEW: Crawl-related commands
├── ariafetcher.py           # EXISTING: Embedded aria2c manager (update to use loguru)
└── aria_downloader.py       # NEW: Download orchestration logic
```

### Data Flow

1. **CLI Layer** (`cli.py` + `crawl_commands.py`)
   - Parse command arguments and options
   - Read URLs from file or stdin
   - Validate and filter URLs

2. **Download Orchestrator** (`aria_downloader.py`)
   - Launch aria2c subprocess via `ariafetcher.py`
   - Submit URLs to aria2c via XML-RPC
   - Monitor download progress
   - Handle completion and errors
   - Clean up subprocess

3. **Subprocess Manager** (`ariafetcher.py`)
   - Start aria2c on ephemeral port
   - Verify TCP and XML-RPC readiness
   - Provide subprocess lifecycle management

## Implementation Checklist

### Phase 0: Logging Infrastructure

**Goal**: Migrate from print statements to structured logging using loguru.

- [ ] Add loguru dependency to project
  - [ ] Add `loguru` to `pyproject.toml` dependencies
  - [ ] Run `uv sync` to install
- [ ] Create `logging_config.py` module
  - [ ] Import loguru's `logger`
  - [ ] Create `setup_logging(verbose=False)` function
  - [ ] Configure default log format: `<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>`
  - [ ] Set default log level to INFO (or DEBUG if verbose=True)
  - [ ] Configure log output to stderr (keeps stdout clean for data)
  - [ ] Add option to write logs to file in app directory
- [ ] Create logger instance getter
  - [ ] Export `get_logger(name)` function that returns configured logger
  - [ ] Support module-level logger creation
- [ ] Update `ariafetcher.py` to use loguru
  - [ ] Replace print statements with `logger.info()`, `logger.debug()`, `logger.error()`
  - [ ] Add debug logging for subprocess startup details
  - [ ] Add error logging for connection failures
- [ ] Update CLI to initialize logging
  - [ ] Call `setup_logging()` in main `cli()` function
  - [ ] Pass `verbose` flag from commands to logging setup
  - [ ] Ensure logging is configured before any commands run

**Benefits**:
- Structured, consistent logging across the application
- Easy to filter by log level (DEBUG, INFO, WARNING, ERROR)
- Can redirect to files for debugging
- Better than scattered print statements
- Plays well with Rich console output

### Phase 1: CLI Structure

- [ ] Add `crawl` subgroup to `cli.py`
  - [ ] Create `@cli.group()` decorator function
  - [ ] Add `@click.pass_context` for context passing
  - [ ] Add docstring explaining crawl commands

### Phase 2: Command Module

- [ ] Create `crawl_commands.py` module
  - [ ] Import necessary dependencies (click, rich, Path, sys)
  - [ ] Create `aria` command with Click decorators
  - [ ] Add `FILENAME` argument (optional, default stdin)
  - [ ] Add `-d/--directory` option
  - [ ] Add `-j/--max-concurrent` option
  - [ ] Add `-v/--verbose` option
  - [ ] Add `--secret` option for RPC security
  - [ ] Implement URL reading logic
    - [ ] Handle file input (read lines from file)
    - [ ] Handle stdin input (check if filename is `-` or None)
    - [ ] Strip whitespace and skip empty lines
    - [ ] Skip comment lines (starting with `#`)
  - [ ] Add basic URL validation (starts with http/https)
  - [ ] Register command with `crawl` group in `cli.py`

### Phase 3: Download Orchestrator

- [ ] Create `aria_downloader.py` module
  - [ ] Create `AriaDownloader` class
    - [ ] `__init__(directory, max_concurrent, secret, verbose)`
    - [ ] `start()` - Launch aria2c subprocess
    - [ ] `add_urls(urls)` - Add URLs to aria2c queue
    - [ ] `monitor_progress()` - Poll download status
    - [ ] `wait_for_completion()` - Block until all done
    - [ ] `stop()` - Clean shutdown of subprocess
  - [ ] Implement XML-RPC communication
    - [ ] Create `xmlrpc.client.ServerProxy` instance
    - [ ] Implement `aria2.addUri(uris, options)` calls
    - [ ] Implement `aria2.tellActive()` for active downloads
    - [ ] Implement `aria2.tellWaiting()` for queued downloads
    - [ ] Implement `aria2.tellStopped()` for completed/failed
    - [ ] Handle RPC secret token in all calls
  - [ ] Add download options
    - [ ] Set `dir` option for download directory
    - [ ] Set `max-concurrent-downloads` option
    - [ ] Set `continue=true` for resume support
    - [ ] Set `check-integrity=true` for checksums
  - [ ] Implement progress display
    - [ ] Use `rich.progress.Progress` for progress bars
    - [ ] Show download speed and ETA
    - [ ] Display file names being downloaded
    - [ ] Show summary at completion
  - [ ] Add error handling
    - [ ] Catch XML-RPC errors
    - [ ] Handle individual download failures
    - [ ] Report failed URLs with error messages
    - [ ] Continue on partial failures

### Phase 4: Integration

- [ ] Wire up `crawl_commands.py` to use `AriaDownloader`
  - [ ] Instantiate `AriaDownloader` with CLI options
  - [ ] Call `start()` and handle startup failures
  - [ ] Pass URLs via `add_urls()`
  - [ ] Call `wait_for_completion()` to block
  - [ ] Ensure `stop()` is called in finally block
- [ ] Add signal handling for graceful shutdown
  - [ ] Catch `KeyboardInterrupt` (Ctrl+C)
  - [ ] Clean up aria2c subprocess on interrupt
  - [ ] Show partial results before exit

### Phase 5: Testing & Polish

- [ ] Manual testing
  - [ ] Test with small file list (2-3 URLs)
  - [ ] Test with stdin input
  - [ ] Test with various file sizes
  - [ ] Test concurrent downloads
  - [ ] Test error cases (404, invalid URLs)
  - [ ] Test interruption (Ctrl+C)
- [ ] Add help text and examples
  - [ ] Write detailed command docstring
  - [ ] Add usage examples to help output
- [ ] Error message improvements
  - [ ] Clear messages for missing aria2c binary
  - [ ] Helpful error for port binding failures
  - [ ] Readable output for download failures

## Technical Details

### URL Input Format

The input file or stdin should contain one URL per line:

```
https://example.com/file1.mp3
https://example.com/file2.pdf
# This is a comment and will be skipped

https://example.com/file3.zip
```

### aria2c Configuration

Default options passed to aria2c:
- `--enable-rpc=true`
- `--rpc-listen-port=<random>`
- `--rpc-listen-all=false` (localhost only)
- `--disable-ipv6=false`
- `--check-integrity=true` (verify checksums)
- `--continue=true` (resume support)
- `--max-concurrent-downloads=<from CLI>`

### XML-RPC API Methods Used

**Note**: When using `--rpc-secret`, all methods require the secret token as the first parameter in the format `"token:SECRET"`.

- `aria2.addUri([uris], options)` - Add download (uris is an array, can contain multiple URLs for mirrors)
- `aria2.tellActive([keys])` - Get active downloads (optional keys parameter)
- `aria2.tellWaiting(offset, num, [keys])` - Get queued downloads
- `aria2.tellStopped(offset, num, [keys])` - Get completed/failed
- `aria2.getGlobalStat()` - Get overall statistics

### Progress Display

Use Rich library for nice terminal output:
- Progress bars for each active download
- Overall statistics (speed, downloaded, remaining)
- Color-coded status (green=complete, red=error, yellow=active)
- Summary table at end showing success/failure counts

## Error Handling Strategy

1. **Startup Errors**: If aria2c fails to start, exit immediately with clear error
2. **Download Errors**: Continue with other URLs, collect errors for final report
3. **Interrupt**: Gracefully stop aria2c and show partial results
4. **Invalid URLs**: Skip and warn, continue with valid URLs

## Future Enhancements

- [ ] Support for torrent files and magnet links
- [ ] Resume previous download session
- [ ] Download with authentication (basic/digest)
- [ ] Proxy support
- [ ] Rate limiting options
- [ ] Integration with retrocast database (track downloaded episodes)
- [ ] Batch download of episodes from specific feeds

# Implementation

- Added a centralized Loguru-powered logging configuration and wired it into the CLI bootstrap and aria2 lifecycle so verbose and non-verbose runs share consistent formatting and file/console handling.
- Implemented an `AriaDownloader` orchestrator that manages an embedded aria2c instance via XML-RPC, providing queue management, lifecycle control, and rich progress reporting for downloads sourced from files or stdin.
- Introduced a `crawl` CLI command group with an `aria` subcommand that parses URL sources, configures download directories and concurrency, surfaces completion summaries, and gracefully handles failures and interrupts.
