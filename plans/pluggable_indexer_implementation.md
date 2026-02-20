# Pluggable Vector Indexer Architecture for Retrocast

## Overview

This plan describes the design and step-by-step implementation of a pluggable vector
search/indexing framework for retrocast, using [pluggy](https://pluggy.readthedocs.io/en/stable/)
as the plugin machinery — modeled closely on Simon Willison's
[llm](https://github.com/simonw/llm) library.

The goal is to allow multiple vector search backends (USearch, ChromaDB, zvec, and
future engines) to be registered, selected, and used interchangeably for indexing
and querying podcast transcript content, without baking any one backend into the core
codebase.

**Default Backend: USearch** — We use [USearch](https://github.com/unum-cloud/usearch)
as the default vector indexer due to its minimal dependencies, high performance,
simple file-based persistence, and permissive Apache 2.0 license.

### V1 Scope

This plan covers **semantic similarity search** over transcript segments:
- Embedding text segments into vectors
- Storing vectors in a pluggable backend
- Searching by semantic similarity

**Explicitly out of scope for V1:**
- Hybrid search (FTS + vectors)
- Custom chunking strategies (core owns chunking)
- `register_commands` hook (plugins cannot add CLI commands in V1)
- `plugin install/uninstall` commands (users use pip/uv directly in V1)

---

## Motivation & Current State

Today the `index/manager.py` module directly imports and instantiates `chromadb`.  
The `index_commands.py` CLI hard-codes `ChromaDBManager`. This coupling makes it
impossible to swap engines without code changes.

The refactor will:

1. Define an abstract `IndexerBackend` base class (the "contract" every backend must satisfy).
2. Use **pluggy** hook specifications to let external packages (or built-in
   defaults) register backend instances.
3. Introduce a `retrocast plugin` CLI group for discovering and inspecting installed plugins.
4. Refactor `index` CLI commands to be backend-agnostic, selecting the active backend
   via a `--backend` option (defaulting to `usearch`).
5. Ship USearch as the **built-in default plugin** and ChromaDB as an optional plugin
   for users who prefer it.

---

## Why USearch as Default?

| Aspect | USearch | ChromaDB |
|--------|---------|----------|
| **Dependencies** | Minimal (numpy only) | Heavy (many transitive deps) |
| **Installation Size** | ~5MB | ~100MB+ |
| **Persistence** | Simple file (`.usearch`) | Directory with SQLite + files |
| **Performance** | Very fast HNSW | Good, but more overhead |
| **Embedding** | BYO (bring your own) | Built-in sentence-transformers |
| **Metadata** | External (SQLite) | Built-in |
| **License** | Apache 2.0 | Apache 2.0 |
| **Memory Mapping** | Native `view()` support | No |

USearch's "bring your own embeddings" model fits retrocast well since we already have
transcription data in SQLite and can store metadata there. The lightweight dependency
footprint makes installation faster and reduces conflicts.

---

## Architectural Overview

```
retrocast (core)
├── plugins.py           ← pluggy PluginManager setup + load_plugins()
├── hookspecs.py         ← HookspecMarker + hook signatures
├── indexer.py           ← Abstract IndexerBackend base class + get_backends() helper
├── embeddings.py        ← Embedding provider abstraction (for USearch and others)
├── default_plugins/
│   ├── usearch_backend.py   ← built-in USearch plugin (DEFAULT)
│   └── chromadb_backend.py  ← optional ChromaDB plugin (for backwards compat)
├── index_commands.py    ← refactored: backend-agnostic, uses hook system
└── cli.py               ← adds `plugin` group

External packages (optional, pip-installed separately):
├── retrocast-zvec        → entry_point group "retrocast", registers ZvecBackend
└── retrocast-faiss       → entry_point group "retrocast", registers FaissBackend
```

### Application Directory Management

Retrocast uses the `platformdirs` library to manage platform-specific and user-specific
application directories. The existing `src/retrocast/appdir.py` module provides helper
functions for locating files and directories. **All index-related storage must use these
helpers** to ensure consistent, platform-appropriate file placement.

**Existing `appdir.py` functions:**

```python
# src/retrocast/appdir.py (existing)
from pathlib import Path
import platformdirs

RETROCAST_APP_NAME = "net.memexponent.retrocast"

def get_app_dir(*, create: bool = False) -> Path:
    """Get the application directory for retrocast.
    Uses platformdirs.user_data_dir() for platform-specific location.
    """
    app_dir = Path(platformdirs.user_data_dir(RETROCAST_APP_NAME, "retrocast"))
    if create and not app_dir.exists():
        app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

def ensure_app_dir() -> Path:
    """Ensure the application directory exists and return the path."""
    return get_app_dir(create=True)

def get_auth_path(*, create: bool = False) -> Path:
    """Get the path to the auth.json file."""
    return get_app_dir(create=create) / "auth.json"

def get_default_db_path(*, create: bool = False) -> Path:
    """Get the default path to the database file."""
    return get_app_dir(create=create) / "retrocast.db"
```

**Current ChromaDB usage pattern (in `index_commands.py`):**

```python
# How ChromaDB currently gets its storage directory
from retrocast.appdir import get_app_dir

app_dir = get_app_dir(create=True)
chroma_dir = app_dir / "chromadb"
chroma_manager = ChromaDBManager(chroma_dir)
```

**New index-related helpers to add to `appdir.py`:**

```python
# Additional functions for index_commands.py (to be added in Phase 1.7)

def get_index_dir(*, create: bool = False) -> Path:
    """Get the base directory for all vector index backends.
    
    Returns:
        Path to <app_dir>/indexes/
    """
    index_dir = get_app_dir(create=create) / "indexes"
    if create and not index_dir.exists():
        index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir

def get_backend_index_dir(backend_id: str, *, create: bool = False) -> Path:
    """Get the storage directory for a specific backend.
    
    Each backend gets its own subdirectory to avoid conflicts.
    
    Args:
        backend_id: The backend identifier (e.g., "usearch", "chromadb")
        create: Whether to create the directory if it doesn't exist
        
    Returns:
        Path to <app_dir>/indexes/<backend_id>/
        
    Example:
        >>> get_backend_index_dir("usearch", create=True)
        Path('/Users/alice/Library/Application Support/net.memexponent.retrocast/indexes/usearch')
    """
    backend_dir = get_index_dir(create=create) / backend_id
    if create and not backend_dir.exists():
        backend_dir.mkdir(parents=True, exist_ok=True)
    return backend_dir

def get_backends_config_path(*, create: bool = False) -> Path:
    """Get the path to the backends configuration file.
    
    Returns:
        Path to <app_dir>/backends.json
    """
    return get_app_dir(create=create) / "backends.json"
```

**Platform-specific paths (via `platformdirs`):**

| Platform | App Directory |
|----------|---------------|
| macOS | `~/Library/Application Support/net.memexponent.retrocast/` |
| Linux | `~/.local/share/net.memexponent.retrocast/` |
| Windows | `C:\Users\<user>\AppData\Local\retrocast\net.memexponent.retrocast\` |

**Directory structure after indexing:**

```
<app_dir>/
├── retrocast.db              # Main SQLite database
├── auth.json                 # Overcast authentication
├── backends.json             # Backend configuration (Phase 9)
└── indexes/
    ├── usearch/              # USearch backend storage
    │   ├── vectors.usearch   # USearch index file
    │   └── metadata.db       # Metadata SQLite database
    └── chromadb/             # ChromaDB backend storage (if used)
        └── chroma.sqlite3    # ChromaDB's internal storage
```

### Plugin Discovery Flow

1. `retrocast/plugins.py` creates a `pluggy.PluginManager("retrocast")`.
2. `load_plugins()` calls `pm.load_setuptools_entrypoints("retrocast")` to discover
   any installed third-party plugins.
3. Built-in default plugins (USearch, optionally ChromaDB) are registered explicitly in `load_plugins()`.
4. CLI commands call `load_plugins()` then use `pm.hook.register_indexer_backends(register=...)`.

### IndexerBackend Contract

The `IndexerBackend` abstract base class defines the contract that all vector search
backends must implement. **Critically, the ingestion API uses an iterator-based approach
to decouple backends from the `Datastore` abstraction** — backends receive data through
a simple iterator of `TranscriptionSegment` dicts, not direct database access.

```python
# retrocast/indexer.py (abstract base class — no pluggy coupling here)
from typing import Any, Iterator, TypedDict

class TranscriptionSegment(TypedDict):
    """A single transcription segment for indexing.
    
    This is the data contract between core and backends. Backends receive
    these dicts via an iterator — they never touch the database directly.
    """
    segment_id: str           # Unique ID (e.g., "t{transcription_id}_s{segment_index}")
    text: str                 # The text content to embed and search
    metadata: dict[str, Any]  # All other fields (timestamps, podcast_title, etc.)


class IndexerBackend:
    """Abstract base class for vector search backends.
    
    Subclasses must set class attributes and implement all abstract methods.
    """
    backend_id: str        # e.g. "usearch", "chromadb", "zvec"
    display_name: str      # Human-readable name for UI display
    
    # Index versioning — increment when index format changes
    index_version: str = "1.0"

    def is_available(self) -> tuple[bool, str]:
        """Check if this backend can be used on the current system.
        
        This method should perform a quick, non-intrusive check for:
        - Required libraries are importable (use check_import() helper)
        - Platform compatibility (e.g., mlx only on macOS)
        
        This method should NOT:
        - Actually initialize the backend or connect to services
        - Check file permissions or validate configuration
        - Perform any slow operations
        
        Returns:
            (True, ""): Backend is available
            (False, reason): Backend is not available with human-readable reason
            
        Note: This method must not raise exceptions. Catch any errors internally
        and return (False, str(exc)) instead.
        """
        return (True, "")
    
    @staticmethod
    def check_import(module_name: str, package_name: str | None = None) -> tuple[bool, str]:
        """Helper to check if a module can be imported without importing it.
        
        Args:
            module_name: Module to check (e.g., "usearch")
            package_name: Package name for installation hint (defaults to module_name)
            
        Returns:
            (True, "") if importable, (False, reason) otherwise
        """
        import importlib.util
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                pkg = package_name or module_name
                return (False, f"Required package '{pkg}' is not installed.")
            return (True, "")
        except (ImportError, ModuleNotFoundError):
            pkg = package_name or module_name
            return (False, f"Required package '{pkg}' is not installed.")

    def configure(self, storage_dir: Path, config: dict[str, Any] | None = None) -> None:
        """Configure the backend with storage location and optional settings.
        
        Args:
            storage_dir: Directory path for backend persistence
            config: Optional backend-specific configuration dict
            
        Raises:
            ImportError: If required dependencies are not installed (with install hint)
            ValueError: If configuration is invalid
        """
        ...

    def index_segments(
        self, 
        segments: Iterator[TranscriptionSegment], 
        batch_size: int = 100
    ) -> int:
        """Index transcription segments from an iterator.
        
        This is the primary ingestion method. The core retrieves data from the
        database and provides it as an iterator of TranscriptionSegment dicts.
        Backends never need to know about Datastore or SQL.
        
        Args:
            segments: Iterator of TranscriptionSegment dicts to index
            batch_size: Hint for batching operations (backends may ignore)
            
        Returns:
            Number of segments successfully indexed
        """
        ...

    def search(
        self, 
        query: str, 
        n_results: int = 5, 
        podcast_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Search indexed segments using semantic similarity.
        
        Args:
            query: The search query text
            n_results: Maximum number of results to return
            podcast_filter: Optional podcast title to filter results
            
        Returns:
            List of matching segments with metadata and distance/score
        """
        ...

    def get_count(self) -> int:
        """Get the number of segments currently indexed.
        
        Returns:
            Number of indexed segments
        """
        ...

    def reset(self) -> None:
        """Clear all indexed data. Used for full rebuilds."""
        ...
    
    def get_index_metadata(self) -> dict[str, Any]:
        """Get metadata about the current index state.
        
        Returns:
            Dict containing at minimum:
            - "version": str (the index_version when index was built)
            - "segment_count": int
            - "created_time": str (ISO format) or None
            - "backend_id": str
        """
        ...
    
    def get_config_schema(self) -> dict[str, Any] | None:
        """Return JSON Schema for this backend's configuration.
        
        Used by `retrocast index vector configure` to prompt for settings.
        
        Returns:
            JSON Schema dict describing configurable options, or None if
            this backend has no configurable options beyond storage_dir.
        """
        return None
```

### Separation of Responsibilities: Core vs Backend

A key architectural principle is that **backends are thin** — they only handle vector
storage and retrieval. All data preparation happens in core.

| Responsibility | Owner | Rationale |
|----------------|-------|-----------|
| Transcript retrieval from SQLite | **Core** | Backends don't touch `Datastore` |
| Chunking / segmentation | **Core** | Consistent behavior across backends |
| Metadata normalization | **Core** | Uniform metadata schema |
| Generating embeddings | **Core** (via `EmbeddingProvider`) | Backends receive pre-computed vectors or delegate to core |
| Vector storage | **Backend** | Backend-specific persistence |
| Similarity search | **Backend** | Backend-specific algorithms |
| Filtering by metadata | **Backend** | Applied during search |

**Backends must NOT:**
- Import or use `Datastore` directly
- Implement their own chunking logic
- Define their own metadata schemas

**Backends receive:**
- An iterator of `TranscriptionSegment` dicts (already chunked, with normalized metadata)
- A `storage_dir` path (from `appdir` helpers)
- Optional configuration dict

This separation ensures:
- Fewer backend implementations to maintain
- Consistent results across engines
- Simpler testing (backends can be tested with mock data)
- Clear path to future features (hybrid search, multiple embedders)

### Hook Specifications

**V1 implements a single hook:**

```python
@hookspec
def register_indexer_backends(register):
    """Register IndexerBackend instances.
    `register` is a callable: register(backend_instance)
    """
```

**Deferred to V2:** A `register_commands(cli)` hook for plugins to add CLI commands.
This is intentionally omitted from V1 to keep the plugin surface area small and stable.

---

## Embedding Provider Abstraction

Since USearch (and other pure vector stores) require pre-computed embeddings, we need
an embedding provider abstraction. This is separate from the indexer backend.

```python
# retrocast/embeddings.py

from abc import ABC, abstractmethod
from typing import Iterator
import numpy as np

class EmbeddingProvider(ABC):
    """Abstract base class for text embedding providers."""
    
    provider_id: str
    display_name: str
    embedding_dim: int  # Dimension of output vectors
    
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        ...
    
    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text. Default implementation calls embed_texts."""
        return self.embed_texts([text])[0]


class SentenceTransformerProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers library."""
    
    provider_id = "sentence-transformers"
    display_name = "Sentence Transformers"
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. Install with:\n"
                "  pip install sentence-transformers"
            )
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI API."""
    
    provider_id = "openai"
    display_name = "OpenAI Embeddings"
    embedding_dim = 1536  # text-embedding-ada-002
    
    def __init__(self, model: str = "text-embedding-ada-002"):
        import os
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai is not installed. Install with:\n"
                "  pip install openai"
            )
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
    
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        response = self.client.embeddings.create(input=texts, model=self.model)
        return np.array([e.embedding for e in response.data])


# Default provider factory
def get_embedding_provider(provider_id: str = "sentence-transformers", **kwargs) -> EmbeddingProvider:
    """Get an embedding provider by ID."""
    providers = {
        "sentence-transformers": SentenceTransformerProvider,
        "openai": OpenAIEmbeddingProvider,
    }
    if provider_id not in providers:
        raise ValueError(f"Unknown embedding provider: {provider_id}")
    return providers[provider_id](**kwargs)
```

---

## Implementation Steps

### Phase 1 — Core Plugin Infrastructure

- [ ] **1.1** Add `pluggy` and `usearch` to `[project.dependencies]` in `pyproject.toml`.
  Move `chromadb` to `[project.optional-dependencies.chromadb]`.

  ```toml
  [project]
  dependencies = [
      # ... existing deps ...
      "pluggy>=1.0.0",
      "usearch>=2.0.0",
      "numpy>=1.20.0",
  ]
  
  [project.optional-dependencies]
  chromadb = ["chromadb>=0.4.0"]
  embeddings = ["sentence-transformers>=2.0.0"]
  all = ["chromadb>=0.4.0", "sentence-transformers>=2.0.0"]
  ```

- [ ] **1.2** Create `src/retrocast/hookspecs.py`:
  - Define `hookspec = HookspecMarker("retrocast")`.
  - Define `hookimpl = HookimplMarker("retrocast")`.
  - Add `register_indexer_backends(register)` hookspec.

- [ ] **1.3** Create `src/retrocast/plugins.py`:
  - Instantiate `pm = pluggy.PluginManager("retrocast")`.
  - Register hookspecs via `pm.add_hookspecs(hookspecs)`.
  - Implement `load_plugins()` with robust error handling (see Phase 1.3a below).
  - Implement `get_plugins(all=False) -> list[dict]` returning name, hooks, version.
  - Implement `get_failed_plugins() -> list[tuple[str, Exception]]` for diagnostics.

- [ ] **1.3a** Implement robust error handling in `load_plugins()`:

  ```python
  import importlib
  import importlib.metadata as metadata
  import os
  import sys
  from loguru import logger

  # Track failed plugins for later reporting
  _failed_plugins: list[tuple[str, Exception]] = []
  _loaded = False
  
  # Our own registry mapping plugin modules to their distribution info.
  # This avoids mutating pluggy's private `pm._plugin_distinfo` attribute.
  _plugin_distinfo: dict[object, metadata.Distribution | None] = {}

  RETROCAST_LOAD_PLUGINS = os.environ.get("RETROCAST_LOAD_PLUGINS", None)

  def load_plugins(*, load_entrypoints: bool = True) -> None:
      """Load all registered plugins with robust error handling.
      
      Plugin loading failures are logged but do not prevent retrocast from starting.
      Use get_failed_plugins() to retrieve any plugins that failed to load.
      
      Args:
          load_entrypoints: If False, skip external plugin discovery (for testing).
                           Default True. Can also be disabled via sys._called_from_test
                           sentinel or RETROCAST_LOAD_PLUGINS="" environment variable.
      """
      global _loaded, _failed_plugins
      if _loaded:
          return
      _loaded = True
      _failed_plugins = []

      # Determine whether to load external plugins
      skip_external = (
          not load_entrypoints
          or hasattr(sys, "_called_from_test")
          or RETROCAST_LOAD_PLUGINS == ""
      )

      if skip_external:
          logger.debug("Skipping external plugin discovery")
      elif RETROCAST_LOAD_PLUGINS is not None:
          # Comma-separated list = load only named packages
          for pkg_name in RETROCAST_LOAD_PLUGINS.split(","):
              pkg_name = pkg_name.strip()
              if pkg_name:
                  _load_plugin_package(pkg_name)
      else:
          # Default: load all installed plugins via setuptools entrypoints
          _load_all_entrypoint_plugins()

      # Always load built-in default plugins
      _load_default_plugins()

  def _load_all_entrypoint_plugins() -> None:
      """Load plugins from all installed packages with 'retrocast' entry points."""
      try:
          for dist in metadata.distributions():
              eps = [ep for ep in dist.entry_points if ep.group == "retrocast"]
              for ep in eps:
                  try:
                      mod = ep.load()
                      pm.register(mod, name=ep.name)
                      _plugin_distinfo[mod] = dist  # Track in our own registry
                      logger.debug(f"Loaded plugin '{ep.name}' from {dist.name}")
                  except Exception as exc:
                      _failed_plugins.append((f"{dist.name}:{ep.name}", exc))
                      logger.warning(
                          f"Failed to load plugin '{ep.name}' from {dist.name}: {exc}"
                      )
      except Exception as exc:
          logger.error(f"Error discovering plugins: {exc}")

  def _load_plugin_package(pkg_name: str) -> None:
      """Load plugins from a specific named package."""
      try:
          dist = metadata.distribution(pkg_name)
          eps = [ep for ep in dist.entry_points if ep.group == "retrocast"]
          for ep in eps:
              try:
                  mod = ep.load()
                  pm.register(mod, name=ep.name)
                  _plugin_distinfo[mod] = dist  # Track in our own registry
                  logger.debug(f"Loaded plugin '{ep.name}' from {pkg_name}")
              except Exception as exc:
                  _failed_plugins.append((f"{pkg_name}:{ep.name}", exc))
                  logger.warning(f"Failed to load plugin '{ep.name}' from {pkg_name}: {exc}")
      except metadata.PackageNotFoundError:
          logger.warning(f"Plugin package '{pkg_name}' not found")
          _failed_plugins.append((pkg_name, metadata.PackageNotFoundError(pkg_name)))

  def _load_default_plugins() -> None:
      """Load built-in default plugins. Failures here are critical errors."""
      for plugin_path in DEFAULT_PLUGINS:
          try:
              mod = importlib.import_module(plugin_path)
              pm.register(mod, plugin_path)
              _plugin_distinfo[mod] = None  # Built-in, no distribution
              logger.debug(f"Loaded built-in plugin '{plugin_path}'")
          except Exception as exc:
              # Built-in plugins failing is a critical error — re-raise
              logger.critical(f"Failed to load built-in plugin '{plugin_path}': {exc}")
              raise

  def get_failed_plugins() -> list[tuple[str, Exception]]:
      """Return list of (plugin_name, exception) for plugins that failed to load."""
      return list(_failed_plugins)
  
  def get_plugin_distinfo(plugin: object) -> metadata.Distribution | None:
      """Get distribution info for a plugin, or None if built-in."""
      return _plugin_distinfo.get(plugin)
  ```

- [ ] **1.4** Create `src/retrocast/indexer.py`:
  - Define the `TranscriptionSegment` TypedDict.
  - Define the abstract `IndexerBackend` base class with the full contract above.
  - Include the `check_import()` static helper method.
  - Implement `get_backends() -> dict[str, IndexerBackend]`:
    - Calls `load_plugins()`.
    - Iterates `pm.hook.register_indexer_backends(register=register)`.
    - **Detects backend ID collisions** and raises a clear error:
      ```python
      def get_backends() -> dict[str, IndexerBackend]:
          """Get all registered backends, keyed by backend_id.
          
          Raises:
              ValueError: If two plugins register the same backend_id
          """
          load_plugins()
          backends: dict[str, IndexerBackend] = {}
          sources: dict[str, str] = {}  # backend_id -> source description
          
          def register(backend: IndexerBackend) -> None:
              bid = backend.backend_id
              if bid in backends:
                  raise ValueError(
                      f"Backend ID collision: '{bid}' is registered by both "
                      f"'{sources[bid]}' and '{backend.display_name}'. "
                      f"Each backend must have a unique backend_id."
                  )
              backends[bid] = backend
              sources[bid] = backend.display_name
          
          pm.hook.register_indexer_backends(register=register)
          return backends
      ```
    - Returns mapping of `backend_id → backend_instance`.
  - Implement `get_backend(name: str) -> IndexerBackend` with a clear error message
    listing available backend IDs when the requested one isn't found.

- [ ] **1.5** Create `src/retrocast/embeddings.py`:
  - Define `EmbeddingProvider` abstract base class.
  - Implement `SentenceTransformerProvider` (default, requires optional dep).
  - Implement `OpenAIEmbeddingProvider` (alternative).
  - Add `get_embedding_provider()` factory function.

- [ ] **1.6** Add index directory helper functions to `src/retrocast/appdir.py`:

  ```python
  # Add to existing appdir.py
  
  def get_index_dir(*, create: bool = False) -> Path:
      """Get the base directory for all vector index backends.
      
      Returns:
          Path to <app_dir>/indexes/
      """
      index_dir = get_app_dir(create=create) / "indexes"
      if create and not index_dir.exists():
          console.print(f"[bold green]Creating index directory:[/] [blue]{index_dir}[/]")
          index_dir.mkdir(parents=True, exist_ok=True)
      return index_dir

  def get_backend_index_dir(backend_id: str, *, create: bool = False) -> Path:
      """Get the storage directory for a specific backend.
      
      Each backend gets its own subdirectory to avoid conflicts.
      
      Args:
          backend_id: The backend identifier (e.g., "usearch", "chromadb")
          create: Whether to create the directory if it doesn't exist
          
      Returns:
          Path to <app_dir>/indexes/<backend_id>/
      """
      backend_dir = get_index_dir(create=create) / backend_id
      if create and not backend_dir.exists():
          backend_dir.mkdir(parents=True, exist_ok=True)
      return backend_dir

  def get_backends_config_path(*, create: bool = False) -> Path:
      """Get the path to the backends configuration file.
      
      Returns:
          Path to <app_dir>/backends.json
      """
      return get_app_dir(create=create) / "backends.json"
  ```

- [ ] **1.7** Add helper function in `datastore.py` to provide transcription segments
  as an iterator (decoupling backends from SQL):

  ```python
  def iter_transcription_segments(self) -> Iterator[TranscriptionSegment]:
      """Yield transcription segments as dicts for indexing.
      
      This method provides the data contract between Datastore and IndexerBackends.
      Backends receive segments via this iterator — they never execute SQL directly.
      
      Yields:
          TranscriptionSegment dicts with segment_id, text, and metadata
      """
      query = """
          SELECT
              ts.transcription_id,
              ts.segment_index,
              ts.start_time,
              ts.end_time,
              ts.text,
              ts.speaker,
              t.podcast_title,
              t.episode_title,
              t.episode_url,
              t.media_path,
              t.language,
              t.backend,
              t.model_size
          FROM transcription_segments ts
          JOIN transcriptions t ON ts.transcription_id = t.transcription_id
          ORDER BY ts.transcription_id, ts.segment_index
      """
      for row in self.db.execute(query).fetchall():
          yield {
              "segment_id": f"t{row[0]}_s{row[1]}",
              "text": row[4],
              "metadata": {
                  "transcription_id": str(row[0]),
                  "segment_index": str(row[1]),
                  "start_time": float(row[2]),
                  "end_time": float(row[3]),
                  "speaker": str(row[5] or ""),
                  "podcast_title": str(row[6] or ""),
                  "episode_title": str(row[7] or ""),
                  "episode_url": str(row[8] or ""),
                  "media_path": str(row[9] or ""),
                  "language": str(row[10] or ""),
                  "backend": str(row[11] or ""),
                  "model_size": str(row[12] or ""),
              },
          }
  ```

---

### Phase 2 — Built-in USearch Default Plugin

- [ ] **2.1** Create `src/retrocast/default_plugins/` package:
  - Add `__init__.py`.
  - Add `usearch_backend.py` (DEFAULT).
  - Add `chromadb_backend.py` (optional, for backwards compatibility).

- [ ] **2.2** In `usearch_backend.py`:

  ```python
  """USearch vector indexer backend for retrocast.
  
  USearch is the default backend due to its minimal dependencies, high performance,
  and simple file-based persistence.
  
  Key characteristics:
  - Pure vector storage (no built-in metadata or embeddings)
  - Single file persistence (.usearch format)
  - Memory-mapped index support via view()
  - Integer keys only (segment_id mapped to integers)
  
  Metadata is stored separately in SQLite alongside the main retrocast database.
  
  Storage location is determined by the CLI using appdir helpers:
      from retrocast.appdir import get_backend_index_dir
      storage_dir = get_backend_index_dir("usearch", create=True)
      backend.configure(storage_dir)
  
  This results in platform-appropriate paths like:
      macOS:   ~/Library/Application Support/net.memexponent.retrocast/indexes/usearch/
      Linux:   ~/.local/share/net.memexponent.retrocast/indexes/usearch/
      Windows: C:\\Users\\<user>\\AppData\\Local\\retrocast\\...\\indexes\\usearch\\
  """

  from datetime import datetime, timezone
  from pathlib import Path
  from typing import Any, Iterator
  import json
  import sqlite3

  from retrocast.hookspecs import hookimpl
  from retrocast.indexer import IndexerBackend, TranscriptionSegment


  class USearchBackend(IndexerBackend):
      """USearch-based vector search backend (DEFAULT).
      
      This backend stores:
      - Vectors in a .usearch file (HNSW index)
      - Metadata in a SQLite database (metadata.db)
      - Key mappings (segment_id <-> integer key) in the same SQLite DB
      
      The storage_dir is provided by the CLI layer using appdir.get_backend_index_dir().
      Backends should NOT determine their own storage locations.
      """
      
      backend_id = "usearch"
      display_name = "USearch (default)"
      index_version = "1.0"
      
      DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
      DEFAULT_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension
      
      def __init__(self):
          self.index = None
          self.metadata_db = None
          self.storage_dir = None
          self.config = {}
          self.embedding_provider = None
      
      def is_available(self) -> tuple[bool, str]:
          """Check if usearch is importable."""
          return self.check_import("usearch", "usearch")
      
      def configure(self, storage_dir: Path, config: dict[str, Any] | None = None) -> None:
          """Configure the USearch backend.
          
          Note: The storage_dir is provided by the CLI layer using:
              from retrocast.appdir import get_backend_index_dir
              storage_dir = get_backend_index_dir("usearch", create=True)
          
          Backends should NOT call appdir functions directly — the CLI layer
          is responsible for determining storage locations.
          
          Args:
              storage_dir: Directory for index and metadata files (from appdir)
              config: Optional configuration with keys:
                  - metric: Distance metric ('cos', 'l2sq', 'ip') default 'cos'
                  - dtype: Vector dtype ('f32', 'f16', 'i8') default 'f32'
                  - connectivity: HNSW connectivity parameter (default 16)
                  - expansion_add: Index build quality (default 128)
                  - expansion_search: Search quality (default 64)
                  - embedding_model: sentence-transformers model name
                  - embedding_dim: Vector dimension (auto-detected if using sentence-transformers)
          """
          try:
              from usearch.index import Index
          except ImportError as exc:
              raise ImportError(
                  "USearch is not installed. Install with:\n"
                  "  pip install usearch\n"
                  "or:\n"
                  "  uv add usearch"
              ) from exc
          
          self.storage_dir = Path(storage_dir)
          self.storage_dir.mkdir(parents=True, exist_ok=True)
          self.config = config or {}
          
          # Initialize embedding provider
          self._init_embedding_provider()
          
          # Index configuration
          metric = self.config.get("metric", "cos")
          dtype = self.config.get("dtype", "f32")
          connectivity = self.config.get("connectivity", 16)
          expansion_add = self.config.get("expansion_add", 128)
          expansion_search = self.config.get("expansion_search", 64)
          ndim = self.config.get("embedding_dim", self.DEFAULT_EMBEDDING_DIM)
          
          # If using sentence-transformers, get actual dimension
          if self.embedding_provider is not None:
              ndim = self.embedding_provider.embedding_dim
          
          index_path = self.storage_dir / "vectors.usearch"
          
          if index_path.exists():
              # Load existing index
              self.index = Index.restore(str(index_path))
          else:
              # Create new index
              self.index = Index(
                  ndim=ndim,
                  metric=metric,
                  dtype=dtype,
                  connectivity=connectivity,
                  expansion_add=expansion_add,
                  expansion_search=expansion_search,
              )
          
          # Initialize metadata database
          self._init_metadata_db()
      
      def _init_embedding_provider(self) -> None:
          """Initialize the embedding provider."""
          embedding_provider_id = self.config.get("embedding_provider", "sentence-transformers")
          embedding_model = self.config.get("embedding_model", self.DEFAULT_EMBEDDING_MODEL)
          
          try:
              from retrocast.embeddings import get_embedding_provider
              self.embedding_provider = get_embedding_provider(
                  embedding_provider_id, 
                  model_name=embedding_model
              )
          except ImportError:
              # Embedding provider not available — will fail on index/search
              self.embedding_provider = None
      
      def _init_metadata_db(self) -> None:
          """Initialize SQLite database for metadata and key mappings."""
          db_path = self.storage_dir / "metadata.db"
          self.metadata_db = sqlite3.connect(str(db_path))
          self.metadata_db.row_factory = sqlite3.Row
          
          # Create tables
          self.metadata_db.executescript("""
              CREATE TABLE IF NOT EXISTS segment_keys (
                  segment_id TEXT PRIMARY KEY,
                  int_key INTEGER UNIQUE NOT NULL
              );
              
              CREATE TABLE IF NOT EXISTS segment_metadata (
                  segment_id TEXT PRIMARY KEY,
                  text TEXT,
                  metadata_json TEXT,
                  FOREIGN KEY (segment_id) REFERENCES segment_keys(segment_id)
              );
              
              CREATE TABLE IF NOT EXISTS index_info (
                  key TEXT PRIMARY KEY,
                  value TEXT
              );
              
              CREATE INDEX IF NOT EXISTS idx_int_key ON segment_keys(int_key);
          """)
          self.metadata_db.commit()
      
      def _get_next_int_key(self) -> int:
          """Get the next available integer key."""
          cursor = self.metadata_db.execute(
              "SELECT COALESCE(MAX(int_key), -1) + 1 FROM segment_keys"
          )
          return cursor.fetchone()[0]
      
      def _segment_id_to_int_key(self, segment_id: str) -> int:
          """Get or create integer key for a segment ID."""
          cursor = self.metadata_db.execute(
              "SELECT int_key FROM segment_keys WHERE segment_id = ?",
              (segment_id,)
          )
          row = cursor.fetchone()
          if row:
              return row[0]
          
          # Create new mapping
          int_key = self._get_next_int_key()
          self.metadata_db.execute(
              "INSERT INTO segment_keys (segment_id, int_key) VALUES (?, ?)",
              (segment_id, int_key)
          )
          return int_key
      
      def _int_key_to_segment_id(self, int_key: int) -> str | None:
          """Look up segment ID from integer key."""
          cursor = self.metadata_db.execute(
              "SELECT segment_id FROM segment_keys WHERE int_key = ?",
              (int_key,)
          )
          row = cursor.fetchone()
          return row[0] if row else None
      
      def index_segments(
          self, 
          segments: Iterator[TranscriptionSegment], 
          batch_size: int = 100
      ) -> int:
          """Index segments using USearch.
          
          This method:
          1. Collects segments in batches
          2. Generates embeddings for text content
          3. Adds vectors to USearch index
          4. Stores metadata in SQLite
          """
          import numpy as np
          
          if self.embedding_provider is None:
              raise RuntimeError(
                  "No embedding provider configured. Install sentence-transformers:\n"
                  "  pip install sentence-transformers"
              )
          
          indexed_count = 0
          batch_segments = []
          
          for segment in segments:
              batch_segments.append(segment)
              
              if len(batch_segments) >= batch_size:
                  indexed_count += self._index_batch(batch_segments)
                  batch_segments = []
          
          # Final partial batch
          if batch_segments:
              indexed_count += self._index_batch(batch_segments)
          
          # Save index to disk
          self._save_index()
          
          # Update index info
          self._set_index_info("index_version", self.index_version)
          self._set_index_info("created_time", datetime.now(timezone.utc).isoformat())
          self._set_index_info("segment_count", str(indexed_count))
          
          return indexed_count
      
      def _index_batch(self, segments: list[TranscriptionSegment]) -> int:
          """Index a batch of segments."""
          import numpy as np
          
          texts = [s["text"] for s in segments]
          embeddings = self.embedding_provider.embed_texts(texts)
          
          keys = []
          for segment in segments:
              int_key = self._segment_id_to_int_key(segment["segment_id"])
              keys.append(int_key)
              
              # Store metadata
              self.metadata_db.execute(
                  """INSERT OR REPLACE INTO segment_metadata 
                     (segment_id, text, metadata_json) VALUES (?, ?, ?)""",
                  (segment["segment_id"], segment["text"], json.dumps(segment["metadata"]))
              )
          
          self.metadata_db.commit()
          
          # Add to USearch index
          keys_array = np.array(keys, dtype=np.uint64)
          self.index.add(keys_array, embeddings)
          
          return len(segments)
      
      def _save_index(self) -> None:
          """Save the USearch index to disk."""
          index_path = self.storage_dir / "vectors.usearch"
          self.index.save(str(index_path))
      
      def _set_index_info(self, key: str, value: str) -> None:
          """Store index metadata."""
          self.metadata_db.execute(
              "INSERT OR REPLACE INTO index_info (key, value) VALUES (?, ?)",
              (key, value)
          )
          self.metadata_db.commit()
      
      def _get_index_info(self, key: str) -> str | None:
          """Retrieve index metadata."""
          cursor = self.metadata_db.execute(
              "SELECT value FROM index_info WHERE key = ?", (key,)
          )
          row = cursor.fetchone()
          return row[0] if row else None
      
      def search(
          self, 
          query: str, 
          n_results: int = 5, 
          podcast_filter: str | None = None
      ) -> list[dict[str, Any]]:
          """Search for similar segments.
          
          Args:
              query: Search query text
              n_results: Maximum results to return
              podcast_filter: Optional podcast title filter
              
          Returns:
              List of dicts with segment_id, text, metadata, and distance
          """
          if self.embedding_provider is None:
              raise RuntimeError(
                  "No embedding provider configured. Install sentence-transformers:\n"
                  "  pip install sentence-transformers"
              )
          
          # Embed query
          query_embedding = self.embedding_provider.embed_text(query)
          
          # Search index (get more results if filtering)
          search_count = n_results * 3 if podcast_filter else n_results
          matches = self.index.search(query_embedding, search_count)
          
          results = []
          for i in range(len(matches)):
              int_key = int(matches.keys[i])
              distance = float(matches.distances[i])
              
              segment_id = self._int_key_to_segment_id(int_key)
              if segment_id is None:
                  continue
              
              # Get metadata
              cursor = self.metadata_db.execute(
                  "SELECT text, metadata_json FROM segment_metadata WHERE segment_id = ?",
                  (segment_id,)
              )
              row = cursor.fetchone()
              if row is None:
                  continue
              
              metadata = json.loads(row["metadata_json"])
              
              # Apply podcast filter
              if podcast_filter and metadata.get("podcast_title") != podcast_filter:
                  continue
              
              results.append({
                  "segment_id": segment_id,
                  "text": row["text"],
                  "metadata": metadata,
                  "distance": distance,
              })
              
              if len(results) >= n_results:
                  break
          
          return results
      
      def get_count(self) -> int:
          """Get the number of indexed segments."""
          return len(self.index) if self.index else 0
      
      def reset(self) -> None:
          """Clear all indexed data."""
          from usearch.index import Index
          
          # Clear USearch index
          if self.index:
              self.index.clear()
          
          # Clear metadata database
          if self.metadata_db:
              self.metadata_db.executescript("""
                  DELETE FROM segment_metadata;
                  DELETE FROM segment_keys;
                  DELETE FROM index_info;
              """)
              self.metadata_db.commit()
          
          # Remove index file
          index_path = self.storage_dir / "vectors.usearch"
          if index_path.exists():
              index_path.unlink()
      
      def get_index_metadata(self) -> dict[str, Any]:
          """Get metadata about the current index."""
          return {
              "version": self._get_index_info("index_version") or "unknown",
              "segment_count": self.get_count(),
              "created_time": self._get_index_info("created_time"),
              "backend_id": self.backend_id,
              "embedding_model": self.config.get("embedding_model", self.DEFAULT_EMBEDDING_MODEL),
              "metric": self.config.get("metric", "cos"),
          }
      
      def get_config_schema(self) -> dict[str, Any] | None:
          """Return JSON Schema for USearch configuration options."""
          return {
              "type": "object",
              "properties": {
                  "metric": {
                      "type": "string",
                      "enum": ["cos", "l2sq", "ip"],
                      "default": "cos",
                      "description": "Distance metric: cosine, L2 squared, or inner product",
                  },
                  "dtype": {
                      "type": "string",
                      "enum": ["f32", "f16", "i8"],
                      "default": "f32",
                      "description": "Vector quantization type",
                  },
                  "connectivity": {
                      "type": "integer",
                      "default": 16,
                      "description": "HNSW graph connectivity (higher = better recall, more memory)",
                  },
                  "expansion_add": {
                      "type": "integer",
                      "default": 128,
                      "description": "Index build quality (higher = slower build, better recall)",
                  },
                  "expansion_search": {
                      "type": "integer",
                      "default": 64,
                      "description": "Search quality (higher = slower search, better recall)",
                  },
                  "embedding_model": {
                      "type": "string",
                      "default": "all-MiniLM-L6-v2",
                      "description": "Sentence-transformers model for embeddings",
                  },
                  "embedding_provider": {
                      "type": "string",
                      "enum": ["sentence-transformers", "openai"],
                      "default": "sentence-transformers",
                      "description": "Embedding provider to use",
                  },
              },
          }


  @hookimpl
  def register_indexer_backends(register):
      """Register the USearch backend."""
      register(USearchBackend())
  ```

- [ ] **2.3** In `chromadb_backend.py` (optional, for backwards compatibility):

  ```python
  """ChromaDB vector indexer backend for retrocast.
  
  This backend is provided for backwards compatibility and for users who prefer
  ChromaDB's built-in embedding and metadata features.
  
  Requires: pip install chromadb
  
  Storage location is determined by the CLI using appdir helpers:
      from retrocast.appdir import get_backend_index_dir
      storage_dir = get_backend_index_dir("chromadb", create=True)
      backend.configure(storage_dir)
  
  This results in platform-appropriate paths like:
      macOS:   ~/Library/Application Support/net.memexponent.retrocast/indexes/chromadb/
      Linux:   ~/.local/share/net.memexponent.retrocast/indexes/chromadb/
      Windows: C:\\Users\\<user>\\AppData\\Local\\retrocast\\...\\indexes\\chromadb\\
  """

  from datetime import datetime, timezone
  from pathlib import Path
  from typing import Any, Iterator

  from retrocast.hookspecs import hookimpl
  from retrocast.indexer import IndexerBackend, TranscriptionSegment


  class ChromaDBBackend(IndexerBackend):
      """ChromaDB-based vector search backend.
      
      ChromaDB provides built-in embeddings and metadata storage, making it
      a convenient all-in-one solution at the cost of heavier dependencies.
      
      The storage_dir is provided by the CLI layer using appdir.get_backend_index_dir().
      Backends should NOT determine their own storage locations.
      """
      
      backend_id = "chromadb"
      display_name = "ChromaDB"
      index_version = "1.0"
      
      def __init__(self):
          self.client = None
          self.collection = None
          self.storage_dir = None
          self.config = {}
      
      def is_available(self) -> tuple[bool, str]:
          """Check if chromadb is importable."""
          return self.check_import("chromadb")
      
      def configure(self, storage_dir: Path, config: dict[str, Any] | None = None) -> None:
          """Configure the ChromaDB backend."""
          try:
              import chromadb
              from chromadb.config import Settings
          except ImportError as exc:
              raise ImportError(
                  "ChromaDB is not installed. Install with:\n"
                  "  pip install chromadb\n"
                  "or:\n"
                  "  uv sync --extra chromadb"
              ) from exc
          
          self.storage_dir = Path(storage_dir)
          self.storage_dir.mkdir(parents=True, exist_ok=True)
          self.config = config or {}
          
          collection_name = self.config.get("collection_name", "transcription_segments")
          telemetry = self.config.get("anonymized_telemetry", False)
          
          settings = Settings(
              chroma_db_impl="duckdb+parquet",
              persist_directory=str(self.storage_dir),
              anonymized_telemetry=telemetry,
          )
          
          self.client = chromadb.Client(settings)
          self.collection = self.client.get_or_create_collection(
              name=collection_name,
              metadata={
                  "description": "Podcast transcription segments",
                  "index_version": self.index_version,
                  "created_time": datetime.now(timezone.utc).isoformat(),
              },
          )
      
      def index_segments(
          self, 
          segments: Iterator[TranscriptionSegment], 
          batch_size: int = 100
      ) -> int:
          """Index segments using ChromaDB."""
          indexed_count = 0
          batch_docs = []
          batch_metadatas = []
          batch_ids = []
          
          for segment in segments:
              batch_ids.append(segment["segment_id"])
              batch_docs.append(segment["text"])
              batch_metadatas.append(segment["metadata"])
              
              if len(batch_ids) >= batch_size:
                  self.collection.add(
                      documents=batch_docs,
                      metadatas=batch_metadatas,
                      ids=batch_ids,
                  )
                  indexed_count += len(batch_ids)
                  batch_docs, batch_metadatas, batch_ids = [], [], []
          
          # Final partial batch
          if batch_ids:
              self.collection.add(
                  documents=batch_docs,
                  metadatas=batch_metadatas,
                  ids=batch_ids,
              )
              indexed_count += len(batch_ids)
          
          return indexed_count
      
      def search(
          self, 
          query: str, 
          n_results: int = 5, 
          podcast_filter: str | None = None
      ) -> list[dict[str, Any]]:
          """Search for similar segments."""
          where_filter = None
          if podcast_filter:
              where_filter = {"podcast_title": podcast_filter}
          
          results = self.collection.query(
              query_texts=[query],
              n_results=n_results,
              where=where_filter,
          )
          
          output = []
          if results and results["ids"]:
              for i, segment_id in enumerate(results["ids"][0]):
                  output.append({
                      "segment_id": segment_id,
                      "text": results["documents"][0][i] if results["documents"] else "",
                      "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                      "distance": results["distances"][0][i] if results["distances"] else 0.0,
                  })
          
          return output
      
      def get_count(self) -> int:
          """Get the number of indexed segments."""
          return self.collection.count() if self.collection else 0
      
      def reset(self) -> None:
          """Clear all indexed data."""
          if self.collection and self.client:
              self.client.delete_collection(self.collection.name)
              self.collection = self.client.create_collection(
                  name=self.config.get("collection_name", "transcription_segments"),
              )
      
      def get_index_metadata(self) -> dict[str, Any]:
          """Get metadata about the current index."""
          coll_meta = self.collection.metadata or {} if self.collection else {}
          return {
              "version": coll_meta.get("index_version", "unknown"),
              "segment_count": self.get_count(),
              "created_time": coll_meta.get("created_time"),
              "backend_id": self.backend_id,
          }
      
      def get_config_schema(self) -> dict[str, Any] | None:
          """Return JSON Schema for ChromaDB configuration options."""
          return {
              "type": "object",
              "properties": {
                  "collection_name": {
                      "type": "string",
                      "default": "transcription_segments",
                      "description": "Name of the ChromaDB collection",
                  },
                  "anonymized_telemetry": {
                      "type": "boolean",
                      "default": False,
                      "description": "Enable ChromaDB anonymous telemetry",
                  },
              },
          }


  @hookimpl
  def register_indexer_backends(register):
      """Register the ChromaDB backend."""
      register(ChromaDBBackend())
  ```

- [ ] **2.4** Update `DEFAULT_PLUGINS` in `plugins.py`:

  ```python
  # USearch is loaded by default, ChromaDB only if installed
  DEFAULT_PLUGINS = [
      "retrocast.default_plugins.usearch_backend",
  ]
  
  # Optionally load ChromaDB if installed
  def _load_default_plugins() -> None:
      """Load built-in default plugins."""
      for plugin_path in DEFAULT_PLUGINS:
          try:
              mod = importlib.import_module(plugin_path)
              pm.register(mod, plugin_path)
              logger.debug(f"Loaded built-in plugin '{plugin_path}'")
          except Exception as exc:
              logger.critical(f"Failed to load built-in plugin '{plugin_path}': {exc}")
              raise
      
      # Try to load ChromaDB backend if available
      try:
          import chromadb  # noqa: F401
          mod = importlib.import_module("retrocast.default_plugins.chromadb_backend")
          pm.register(mod, "retrocast.default_plugins.chromadb_backend")
          logger.debug("Loaded optional ChromaDB backend")
      except ImportError:
          logger.debug("ChromaDB not installed; chromadb backend not available")
  ```

- [ ] **2.5** Keep `src/retrocast/index/manager.py` temporarily as a thin shim that
  imports from `ChromaDBBackend` (preserves backwards-compatibility for any code that
  imports `ChromaDBManager` directly).

---

### Phase 3 — Refactor Index CLI Commands

- [ ] **3.1** Refactor `index_commands.py`:
  - Remove the direct import of `ChromaDBManager`.
  - Change `--backend` option default from `"chromadb"` to `"usearch"`.
  - Use `get_backend(backend)` to obtain the active backend.
  - **Use the `appdir` module to get storage directories** (following the existing pattern):
    ```python
    from retrocast.appdir import get_backend_index_dir, get_default_db_path
    from retrocast.indexer import get_backend
    from retrocast.backend_config import load_backend_config
    
    @vector.command(name="build")
    @click.option("--backend", "backend_name", default="usearch", 
                  help="Vector index backend to use.")
    @click.option("-d", "--database", "db_path", type=click.Path(...), default=None)
    @click.option("--rebuild", is_flag=True, default=False)
    def build_vector_index(ctx, backend_name, db_path, rebuild):
        # Use appdir helper for database path
        if db_path is None:
            db_path = get_default_db_path(create=False)
        
        # Get backend instance via plugin system
        backend = get_backend(backend_name)
        
        # Use appdir helper for backend-specific storage directory
        storage_dir = get_backend_index_dir(backend_name, create=True)
        console.print(f"[dim]Index storage: {storage_dir}[/dim]")
        
        # Load backend configuration from backends.json
        config = load_backend_config(backend_name)
        
        # Configure backend with storage directory
        backend.configure(storage_dir, config=config)
        
        # ... rest of indexing logic
    ```
  - **Use the iterator-based ingestion API**:
    ```python
    # Core retrieves data, backend doesn't touch the database
    segments = datastore.iter_transcription_segments()
    indexed_count = backend.index_segments(segments, batch_size=batch_size)
    ```
  - Check index version and prompt for rebuild if version mismatch:
    ```python
    index_meta = backend.get_index_metadata()
    if index_meta["version"] != backend.index_version:
        console.print(
            f"[yellow]Index was built with version {index_meta['version']}, "
            f"current is {backend.index_version}.[/yellow]"
        )
        if not rebuild:
            console.print("Run with --rebuild to update the index format.")
            raise click.Abort()
    ```

- [ ] **3.2** Add `retrocast index vector backends` sub-command (see full spec below).

- [ ] **3.3** Refactor or add search command (if present):
  - Apply same `--backend` option pattern (default: `"usearch"`).

#### 3.2 — `retrocast index vector backends` — Full Specification

**Command path:**
```
retrocast index vector backends
```

**Purpose:** List every `IndexerBackend` that is currently registered via the plugin
system, so users can see at a glance which backends are available before choosing one
with `--backend`.

**Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--json` | flag | off | Emit machine-readable JSON instead of the Rich table |
| `--all` | flag | off | Include built-in default backends (normally shown anyway, but makes it explicit and consistent with `plugin list --all`) |

**Default (Rich table) output:**

```
 Installed Index Backends
 ┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
 ┃ Backend ID ┃ Display Name              ┃ Source        ┃ Available ┃
 ┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
 │ usearch    │ USearch (default)         │ built-in      │ ✓         │
 │ chromadb   │ ChromaDB                  │ built-in      │ ✓         │
 │ zvec       │ zvec (zero-copy vectors)  │ retrocast-zvec│ ✗ *       │
 └────────────┴───────────────────────────┴───────────────┴───────────┘
 * zvec: optional dependency 'zvec' not installed.
   Run: retrocast plugin install retrocast-zvec
```

Column definitions:
- **Backend ID** — the string passed to `--backend` on other commands.
- **Display Name** — `backend.display_name` attribute.
- **Source** — `"built-in"` for default plugins; the PyPI package name (from
  `importlib.metadata`) for third-party plugins.
- **Available** — `✓` if the backend's underlying library is importable;
  `✗` with a short reason if the soft import guard in `configure()` / `__init__`
  would fail. Each `IndexerBackend` subclass must implement an
  `is_available() -> tuple[bool, str]` method that returns `(True, "")` or
  `(False, "reason string")` without raising.

**`--json` output shape:**

```json
[
  {
    "backend_id": "usearch",
    "display_name": "USearch (default)",
    "source": "built-in",
    "available": true,
    "unavailable_reason": null
  },
  {
    "backend_id": "chromadb",
    "display_name": "ChromaDB",
    "source": "built-in",
    "available": true,
    "unavailable_reason": null
  },
  {
    "backend_id": "zvec",
    "display_name": "zvec (zero-copy vectors)",
    "source": "retrocast-zvec",
    "available": false,
    "unavailable_reason": "optional dependency 'zvec' not installed"
  }
]
```

**Implementation notes:**

- Call `get_backends()` (which calls `load_plugins()` internally) to get the
  registered backends dict.
- For each backend, call `backend.is_available()` to populate the Available column
  without actually constructing or connecting to the backend.
- Determine **Source** by using our own `get_plugin_distinfo()` registry (not pluggy's
  private `pm._plugin_distinfo`): if the plugin module has a distinfo entry, use
  `distinfo.metadata["Name"]`; otherwise label it `"built-in"`.
- If **no backends at all** are registered (empty dict), print a friendly message:
  ```
  No index backends are registered.
  Install one with: retrocast plugin install retrocast-<backend>
  ```

**Integration with other commands:**

- The `build_vector_index` and search commands should call `backends` logic (or
  `get_backends()`) on startup and surface a clear error if the requested
  `--backend` is not in the registered set, including a hint to run
  `retrocast index vector backends` to see what is available:
  ```
  Error: backend 'zvec' not found.
  Run 'retrocast index vector backends' to see installed backends.
  ```

---

### Phase 4 — `plugin` CLI Group

- [ ] **4.1** Create `src/retrocast/plugin_commands.py`:
  - Define a `plugin` Click group.
  - Add `plugin list` command:
    - Calls `get_plugins(all)`.
    - Prints a Rich table: Name | Version | Hooks.
    - Supports `--all` flag to include built-in default plugins.
    - Supports `--json` flag for machine-readable output.
    - Supports `--hook` filter option to show only plugins implementing a specific hook.
  - Add `plugin list --failed` option to show plugins that failed to load:
    ```python
    @click.option("--failed", is_flag=True, help="Show only plugins that failed to load")
    def plugin_list(all, json, hook, failed):
        if failed:
            failed_plugins = get_failed_plugins()
            if not failed_plugins:
                console.print("[green]No plugins failed to load.[/green]")
                return
            # Display failed plugins with error messages
            ...
    ```

- [ ] **4.2** Wire `plugin` group into the root CLI in `cli.py`:
  ```python
  from retrocast.plugin_commands import plugin
  cli.add_command(plugin)
  ```

- [ ] **4.3** At the end of `cli.py` (after all commands are defined), call:
  ```python
  load_plugins()
  ```


---

### Phase 5 — Entry-point Convention for External Plugins

- [ ] **5.1** Document the entry-point group name (`"retrocast"`) in the developer
  docs / README.

- [ ] **5.2** Add a `pyproject.toml` section showing the entry-point format that
  third-party packages should use:
  ```toml
  [project.entry-points.retrocast]
  zvec = "retrocast_zvec:plugin"
  ```

- [ ] **5.3** Create an example skeleton plugin in `examples/retrocast-zvec-example/`
  (as a reference; no real zvec code required at this stage):
  - `pyproject.toml` with entry-point declaration.
  - `retrocast_zvec/__init__.py` with:
    - `ZvecBackend(IndexerBackend)` stub class.
    - `@hookimpl register_indexer_backends(register)` function.
  - `README.md` explaining how to build and install a retrocast plugin.

---

### Phase 6 — Test Support Utilities

- [ ] **6.1** Create `tests/conftest.py` to configure plugin loading for tests:

  ```python
  import sys
  import pytest
  
  # Sentinel to prevent plugin discovery during tests (fallback mechanism).
  # The preferred approach is to call load_plugins(load_entrypoints=False).
  sys._called_from_test = True
  
  @pytest.fixture(autouse=True)
  def reset_plugin_state():
      """Reset plugin loading state before each test."""
      from retrocast import plugins
      plugins._loaded = False
      plugins._failed_plugins = []
      plugins._plugin_distinfo = {}
      yield
      # Cleanup after test
      plugins._loaded = False
  ```

- [ ] **6.2** Create test fixtures in `tests/fixtures/test_plugins/`:
  - `dummy_backend.py` — **In-memory backend for testing** that requires no vector libraries.
    This allows CLI and integration tests without heavy dependencies:
    ```python
    from retrocast.indexer import IndexerBackend, TranscriptionSegment
    from typing import Any, Iterator
    from pathlib import Path

    class DummyBackend(IndexerBackend):
        """In-memory backend for testing. No external dependencies required.
        
        This backend stores segments in a Python list and performs simple
        substring matching for search. It implements the full IndexerBackend
        contract, making it suitable for:
        - CLI command tests
        - Integration tests without vector libraries
        - Plugin system tests
        """
        
        backend_id = "dummy"
        display_name = "Dummy Backend (for testing)"
        index_version = "1.0"
        
        def __init__(self):
            self._segments: list[TranscriptionSegment] = []
            self._configured = False
        
        def is_available(self) -> tuple[bool, str]:
            return (True, "")  # Always available — no dependencies
        
        def configure(self, storage_dir: Path, config: dict[str, Any] | None = None) -> None:
            self._configured = True
            self._storage_dir = storage_dir
        
        def index_segments(self, segments: Iterator[TranscriptionSegment], batch_size: int = 100) -> int:
            count = 0
            for seg in segments:
                self._segments.append(seg)
                count += 1
            return count
        
        def search(self, query: str, n_results: int = 5, podcast_filter: str | None = None) -> list[dict]:
            # Simple substring search for testing
            results = []
            for s in self._segments:
                if query.lower() in s["text"].lower():
                    if podcast_filter and s["metadata"].get("podcast_title") != podcast_filter:
                        continue
                    results.append({
                        "segment_id": s["segment_id"],
                        "text": s["text"],
                        "metadata": s["metadata"],
                        "distance": 0.0,  # Fake distance
                    })
            return results[:n_results]
        
        def get_count(self) -> int:
            return len(self._segments)
        
        def reset(self) -> None:
            self._segments = []
        
        def get_index_metadata(self) -> dict[str, Any]:
            return {
                "version": self.index_version,
                "segment_count": len(self._segments),
                "created_time": None,
                "backend_id": self.backend_id,
            }
    ```
  - `broken_backend.py` — Intentionally broken (import error) for testing error handling
  - `unavailable_backend.py` — Backend that reports unavailable for testing UI

- [ ] **6.3** Add pytest fixture for temporary plugin registration:

  ```python
  # tests/conftest.py
  import pytest
  from retrocast.hookspecs import hookimpl
  from retrocast.plugins import pm

  @pytest.fixture
  def register_test_backend():
      """Context manager to temporarily register a test backend."""
      registered_modules = []
      
      def _register(backend_instance):
          @hookimpl
          def register_indexer_backends(register):
              register(backend_instance)
          
          # Create a module-like object to register
          test_module = type('TestPluginModule', (), {
              'register_indexer_backends': register_indexer_backends
          })()
          
          pm.register(test_module, name=f'test_backend_{backend_instance.backend_id}')
          registered_modules.append(test_module)
          return backend_instance
      
      yield _register
      
      # Cleanup: unregister all test plugins
      for mod in registered_modules:
          try:
              pm.unregister(mod)
          except ValueError:
              pass  # Already unregistered
  ```

- [ ] **6.4** Add fixture for mocking pip operations:

  ```python
  @pytest.fixture
  def mock_pip_install(mocker):
      """Mock runpy.run_module to prevent actual pip calls during tests."""
      return mocker.patch('runpy.run_module')
  ```

- [ ] **6.5** Write unit tests in `tests/test_plugins.py`:
  - [ ] Test that `load_plugins()` is idempotent (calling it twice doesn't double-register).
  - [ ] Test that `load_plugins(load_entrypoints=False)` skips external plugins.
  - [ ] Test `get_plugins()` excludes default plugins unless `all=True`.
  - [ ] Test that a manually registered plugin appears in `get_plugins()`.
  - [ ] Test that `register_indexer_backends` hook adds a new backend to `get_backends()`.
  - [ ] Test that a broken plugin (raises on load) is caught and added to `get_failed_plugins()`.
  - [ ] Test that `RETROCAST_LOAD_PLUGINS=""` skips external plugins.
  - [ ] Test that `RETROCAST_LOAD_PLUGINS="pkg-a,pkg-b"` loads only named packages.
  - [ ] **Test backend ID collision detection**: register two backends with the same
        `backend_id` and verify `get_backends()` raises `ValueError` with a clear message.

- [ ] **6.6** Write unit tests in `tests/test_index_commands.py`:
  - [ ] Test `build_vector_index` with a mock backend registered via the plugin system.
  - [ ] Test `retrocast index vector backends` default (Rich table) output includes
    Backend ID, Display Name, Source, and Available columns.
  - [ ] Test `retrocast index vector backends --json` produces the correct JSON shape.
  - [ ] Test that a backend whose `is_available()` returns `(False, "reason")` shows
    `✗` in the table and `"available": false` with `"unavailable_reason"` in JSON.
  - [ ] Test that when no backends are registered the command prints the
    "No index backends are registered" message.
  - [ ] Test that an invalid `--backend` name on `build` or `search` prints the
    "Run 'retrocast index vector backends'" hint.

- [ ] **6.7** Write unit tests in `tests/test_plugin_install.py`:
  - [ ] Test that `plugin install` constructs correct `sys.argv` for pip.
  - [ ] Test that `plugin uninstall` constructs correct `sys.argv` for pip.
  - [ ] Test that `-e`/`--editable` option is passed through correctly.
  - [ ] Test that `-y`/`--yes` option is passed through correctly.

- [ ] **6.8** Write integration tests in `tests/integration/test_usearch_backend.py`:
  - [ ] Test full indexing workflow with real USearch (use temp directory).
  - [ ] Verify search returns expected results.
  - [ ] Test rebuild/reset functionality.
  - [ ] Test index versioning metadata is stored and retrieved correctly.
  - [ ] Test index persistence (save/load).

- [ ] **6.9** Write integration tests in `tests/integration/test_chromadb_backend.py`:
  - [ ] Test full indexing workflow with real ChromaDB (use temp directory).
  - [ ] Verify search returns expected results.
  - [ ] Test rebuild/reset functionality.
  - [ ] Test index versioning metadata is stored and retrieved correctly.

---

### Phase 7 — Cleanup & Documentation

- [ ] **7.1** Remove `src/retrocast/index/manager.py` shim once all internal callsites
  use the new `IndexerBackend` API.

- [ ] **7.2** Move `chromadb` from the hard `castchat` optional-dependency group to
  a separate `chromadb` optional group. Ensure the ChromaDB backend's `configure()`
  raises a helpful `ImportError` if chromadb isn't installed.

- [ ] **7.3** Update `AGENTS.md` to document:
  - The new `src/retrocast/plugins.py` and `hookspecs.py` modules.
  - The `retrocast plugin` CLI group.
  - The `--backend` flag on index commands (default: `usearch`).
  - The entry-point convention for external plugins.
  - The `RETROCAST_LOAD_PLUGINS` environment variable.
  - The embedding provider system.

- [ ] **7.4** Update `docs/cli/index.md` (if it exists) to reflect the new
  `retrocast index vector backends` sub-command and `--backend` option.

- [ ] **7.5** Run the full QA suite:
  ```bash
  uv run poe qa
  prek run
  ```

---

## Phase 8 — Plugin Install / Uninstall CLI Commands (V2 — DEFERRED)

> **Note:** This phase is deferred to V2. For V1, users install plugins using standard
> tools (`pip install retrocast-zvec` or `uv add retrocast-zvec`). This keeps V1
> focused on the core backend abstraction and avoids packaging edge cases.

This phase adds first-class CLI support for installing and uninstalling retrocast
backend plugins **into the correct Python environment** — the same environment that
retrocast itself runs in. This mirrors `llm install` / `llm uninstall` exactly.

### The Core Problem: Installing into the Right Environment

Retrocast is typically run via `uv run` (a uv-managed virtual environment) or via a
pipx-isolated environment. If a user runs a plain `pip install retrocast-zvec` in
their shell, the package lands in the *wrong* Python environment and the plugin is
never discovered. The solution — identical to llm's — is to invoke `pip` from within
the same Python process that is already running retrocast, using `runpy.run_module`.
This guarantees the package is installed into the active retrocast environment
regardless of how retrocast was launched.

### 8.1 — `plugin install` Command

- [ ] **8.1** Add `plugin install` sub-command to the `plugin` Click group in
  `plugin_commands.py`:

  ```python
  from runpy import run_module
  import sys

  @plugin.command(name="install")
  @click.argument("packages", nargs=-1, required=False)
  @click.option("-U", "--upgrade", is_flag=True,
                help="Upgrade packages to the latest version")
  @click.option("-e", "--editable",
                help="Install a project in editable mode from this path")
  @click.option("--force-reinstall", is_flag=True,
                help="Reinstall even if already up-to-date")
  @click.option("--no-cache-dir", is_flag=True, help="Disable the pip cache")
  @click.option("--pre", is_flag=True,
                help="Include pre-release and development versions")
  def plugin_install(packages, upgrade, editable, force_reinstall, no_cache_dir, pre):
      """Install retrocast backend plugins from PyPI into the retrocast environment.
      
      Examples:
        retrocast plugin install retrocast-zvec
        retrocast plugin install -e ./my-plugin
        retrocast plugin install -U retrocast-zvec
      
      Note: If a broken plugin prevents retrocast from starting, you can disable
      external plugins temporarily with:
        RETROCAST_LOAD_PLUGINS='' retrocast plugin uninstall <broken-plugin> -y
      """
      args = ["pip", "install"]
      if upgrade:
          args += ["--upgrade"]
      if editable:
          args += ["--editable", editable]
      if force_reinstall:
          args += ["--force-reinstall"]
      if no_cache_dir:
          args += ["--no-cache-dir"]
      if pre:
          args += ["--pre"]
      args += list(packages)
      sys.argv = args
      run_module("pip", run_name="__main__")
  ```

  **Why `runpy.run_module("pip")`?**  
  This executes `pip` as a module inside the *current* Python interpreter's
  environment — the same one where retrocast is running. It is equivalent to
  `python -m pip install ...` but without shelling out, so it always targets the
  right site-packages regardless of whether the user is in a uv venv, pipx
  environment, or a plain venv.

### 8.2 — `plugin uninstall` Command

- [ ] **8.2** Add `plugin uninstall` sub-command:

  ```python
  @plugin.command(name="uninstall")
  @click.argument("packages", nargs=-1, required=True)
  @click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
  def plugin_uninstall(packages, yes):
      """Uninstall retrocast backend plugins from the retrocast environment."""
      sys.argv = ["pip", "uninstall"] + list(packages) + (["-y"] if yes else [])
      run_module("pip", run_name="__main__")
  ```

### 8.3 — Handling Broken Plugins at Startup

A plugin that introduces a syntax error or bad import will cause `load_plugins()` to
raise, preventing retrocast from starting at all. Two mitigations are needed:

- [ ] **8.3a** Error handling is implemented in Phase 1.3a — each individual entrypoint
  load is wrapped in `try/except Exception`. Failed plugins are logged and tracked
  in `_failed_plugins` list, but do not prevent retrocast from starting.

- [ ] **8.3b** Document the recovery escape hatch in help text for `plugin install`
  and in `AGENTS.md`: if a broken plugin prevents retrocast from starting, the user
  can disable all external plugins with the env var to reach `plugin uninstall`:

  ```bash
  RETROCAST_LOAD_PLUGINS='' retrocast plugin uninstall retrocast-broken-plugin -y
  ```

### 8.4 — `RETROCAST_LOAD_PLUGINS` Environment Variable

Implemented in Phase 1.3a. The three-mode behaviour:

| Value | Behaviour |
|---|---|
| Not set | Load all installed plugins via setuptools entrypoints |
| `""` (empty string) | Load **no** external plugins (only built-in defaults) |
| `"pkg-a,pkg-b"` | Load **only** the named packages' retrocast entrypoints |

- [ ] **8.4** Add `RETROCAST_LOAD_PLUGINS` to `plugin list --help` output as a note,
  so users know how to limit plugin loading.

### 8.5 — `plugin list` Enhancements (additions to Phase 4.1)

Update the `plugin list` command with richer output now that install/uninstall exist:

- [ ] **8.5** Add `--hook` filter option to `plugin list` (mirrors `llm plugins
  --hook`), so users can ask "which plugins implement `register_indexer_backends`?":

  ```bash
  retrocast plugin list --hook register_indexer_backends
  ```

- [ ] **8.6** The `--json` output for `plugin list` should match this shape (also
  mirroring llm):

  ```json
  [
    {
      "name": "retrocast-zvec",
      "version": "0.2.1",
      "hooks": ["register_indexer_backends"]
    },
    {
      "name": "retrocast-faiss",
      "version": "0.1.0",
      "hooks": ["register_indexer_backends"]
    }
  ]
  ```

### 8.6 — Developer Workflow for Plugin Authors

The example skeleton (Phase 5.3) should be extended to document the full install
loop a plugin author uses during development:

- [ ] **8.7** Update `examples/retrocast-zvec-example/README.md` with the standard
  development loop:

  ```bash
  # Install your plugin in editable mode into the retrocast environment:
  retrocast plugin install -e .

  # Confirm it is registered:
  retrocast plugin list

  # Test a build command using your new backend:
  retrocast index vector build --backend zvec

  # Uninstall when done:
  retrocast plugin uninstall retrocast-zvec -y
  ```

  And the distribution paths (matching llm's tutorial):
  - **Editable local install**: `retrocast plugin install -e ./path/to/my-plugin`
  - **Wheel file**: `retrocast plugin install dist/retrocast_zvec-0.1-py3-none-any.whl`
  - **GitHub ZIP**: `retrocast plugin install 'https://github.com/user/retrocast-zvec/archive/main.zip'`
  - **PyPI**: `retrocast plugin install retrocast-zvec`

### 8.7 — Entry-point Naming Convention

- [ ] **8.8** Establish and document a naming convention for third-party plugins in
  `AGENTS.md` and the example README:

  | Aspect | Convention | Example |
  |---|---|---|
  | PyPI package name | `retrocast-<backend>` | `retrocast-zvec` |
  | Python module name | `retrocast_<backend>` | `retrocast_zvec` |
  | Entry-point group | `retrocast` | (always `retrocast`) |
  | Entry-point name | `<backend>` | `zvec` |
  | `backend_id` attribute | `<backend>` | `"zvec"` |

  The `pyproject.toml` stanza for a third-party plugin:

  ```toml
  [project]
  name = "retrocast-zvec"
  version = "0.1.0"
  dependencies = ["retrocast"]   # retrocast itself is a dependency

  [project.entry-points.retrocast]
  zvec = "retrocast_zvec"        # points to the module, not a function
  ```

  The top-level `retrocast_zvec/__init__.py` (or `retrocast_zvec.py`) then contains
  the `@hookimpl` decorated functions, exactly as llm plugins work.

---

## Phase 9 — Backend Configuration Management

This phase adds support for backend-specific configuration that persists across
invocations. Some backends may have options beyond just the storage directory
(e.g., collection names, embedding models, connection strings).

### 9.1 — Configuration Storage

- [ ] **9.1** Store backend configurations in `app_dir / "backends.json"`:

  ```json
  {
    "usearch": {
      "metric": "cos",
      "embedding_model": "all-MiniLM-L6-v2",
      "connectivity": 16
    },
    "chromadb": {
      "collection_name": "transcription_segments",
      "anonymized_telemetry": false
    }
  }
  ```

- [ ] **9.2** Add configuration loading/saving utilities in `src/retrocast/backend_config.py`:

  ```python
  import json
  from pathlib import Path
  from typing import Any
  from retrocast.appdir import get_backends_config_path

  def get_config_path() -> Path:
      """Return path to backends.json configuration file.
      
      Uses the appdir module's helper to ensure platform-appropriate location.
      """
      return get_backends_config_path(create=True)

  def load_backend_config(backend_id: str) -> dict[str, Any]:
      """Load configuration for a specific backend.
      
      Returns empty dict if no config exists for this backend.
      """
      config_path = get_config_path()
      if not config_path.exists():
          return {}
      
      try:
          with open(config_path) as f:
              all_config = json.load(f)
          return all_config.get(backend_id, {})
      except (json.JSONDecodeError, IOError):
          return {}

  def save_backend_config(backend_id: str, config: dict[str, Any]) -> None:
      """Save configuration for a specific backend."""
      config_path = get_config_path()
      
      # Load existing config
      all_config = {}
      if config_path.exists():
          try:
              with open(config_path) as f:
                  all_config = json.load(f)
          except (json.JSONDecodeError, IOError):
              pass
      
      # Update and save
      all_config[backend_id] = config
      with open(config_path, "w") as f:
          json.dump(all_config, f, indent=2)

  def validate_config(config: dict[str, Any], schema: dict[str, Any]) -> list[str]:
      """Validate config against JSON schema. Returns list of error messages."""
      # Basic validation — for production, consider jsonschema library
      errors = []
      props = schema.get("properties", {})
      
      for key, value in config.items():
          if key not in props:
              errors.append(f"Unknown configuration key: {key}")
              continue
          
          prop_schema = props[key]
          expected_type = prop_schema.get("type")
          
          if expected_type == "string" and not isinstance(value, str):
              errors.append(f"{key}: expected string, got {type(value).__name__}")
          elif expected_type == "boolean" and not isinstance(value, bool):
              errors.append(f"{key}: expected boolean, got {type(value).__name__}")
          elif expected_type == "integer" and not isinstance(value, int):
              errors.append(f"{key}: expected integer, got {type(value).__name__}")
          elif expected_type == "number" and not isinstance(value, (int, float)):
              errors.append(f"{key}: expected number, got {type(value).__name__}")
      
      return errors
  ```

### 9.2 — Configuration CLI Commands

- [ ] **9.3** Add `retrocast index vector configure <backend>` command:

  ```python
  @vector.command(name="configure")
  @click.argument("backend_name")
  @click.option("--show", is_flag=True, help="Show current configuration without prompting")
  @click.option("--json", "output_json", is_flag=True, help="Output configuration as JSON")
  @click.option("--set", "set_values", multiple=True, help="Set a config value (key=value)")
  @click.pass_context
  def configure_backend(ctx, backend_name, show, output_json, set_values):
      """Configure a vector index backend.
      
      Examples:
        retrocast index vector configure usearch --show
        retrocast index vector configure usearch --set metric=l2sq
        retrocast index vector configure usearch --set embedding_model=all-mpnet-base-v2
        retrocast index vector configure usearch  # Interactive prompts
      """
      from retrocast.indexer import get_backend
      from retrocast.backend_config import load_backend_config, save_backend_config, validate_config
      
      backend = get_backend(backend_name)
      schema = backend.get_config_schema()
      current_config = load_backend_config(backend_name)
      
      if show or output_json:
          # Display current configuration
          if output_json:
              click.echo(json.dumps(current_config, indent=2))
          else:
              console.print(f"[bold]Configuration for {backend.display_name}:[/bold]")
              if current_config:
                  for key, value in current_config.items():
                      console.print(f"  {key}: {value}")
              else:
                  console.print("  [dim](no configuration set)[/dim]")
          return
      
      if set_values:
          # Non-interactive: set specific values
          for kv in set_values:
              if "=" not in kv:
                  console.print(f"[red]Invalid format: {kv} (expected key=value)[/red]")
                  raise click.Abort()
              key, value = kv.split("=", 1)
              # Attempt type coercion based on schema
              if schema and key in schema.get("properties", {}):
                  prop_type = schema["properties"][key].get("type")
                  if prop_type == "boolean":
                      value = value.lower() in ("true", "1", "yes")
                  elif prop_type == "integer":
                      value = int(value)
                  elif prop_type == "number":
                      value = float(value)
              current_config[key] = value
          
          # Validate and save
          if schema:
              errors = validate_config(current_config, schema)
              if errors:
                  for err in errors:
                      console.print(f"[red]Validation error: {err}[/red]")
                  raise click.Abort()
          
          save_backend_config(backend_name, current_config)
          console.print(f"[green]Configuration saved for {backend.display_name}[/green]")
          return
      
      # Interactive mode: prompt for each configurable option
      if not schema:
          console.print(f"[yellow]{backend.display_name} has no configurable options.[/yellow]")
          return
      
      console.print(f"[bold]Configure {backend.display_name}[/bold]")
      console.print("[dim]Press Enter to keep current value[/dim]\n")
      
      for key, prop in schema.get("properties", {}).items():
          current = current_config.get(key, prop.get("default"))
          description = prop.get("description", "")
          prop_type = prop.get("type", "string")
          
          prompt = f"{key}"
          if description:
              prompt += f" ({description})"
          
          if prop_type == "boolean":
              default_str = "yes" if current else "no"
              value = click.prompt(prompt, default=default_str, show_default=True)
              current_config[key] = value.lower() in ("true", "1", "yes", "y")
          else:
              value = click.prompt(prompt, default=str(current) if current else "", show_default=True)
              if value:
                  if prop_type == "integer":
                      current_config[key] = int(value)
                  elif prop_type == "number":
                      current_config[key] = float(value)
                  else:
                      current_config[key] = value
      
      save_backend_config(backend_name, current_config)
      console.print(f"\n[green]Configuration saved for {backend.display_name}[/green]")
  ```

### 9.3 — Integrate Configuration with Backend Lifecycle

- [ ] **9.4** Update `index_commands.py` to load and pass configuration to backends:

  ```python
  from retrocast.backend_config import load_backend_config
  
  # In build_vector_index command:
  config = load_backend_config(backend_name)
  backend.configure(storage_dir, config=config)
  ```

---

## Phase 10 — Index Versioning

This phase adds index versioning to detect when a backend's index format has changed
and prompt users to rebuild.

### 10.1 — Version Tracking

- [ ] **10.1** Each `IndexerBackend` subclass has an `index_version` class attribute
  (default `"1.0"`). When the index format changes incompatibly, increment this.

- [ ] **10.2** Backends store version in index metadata when building:

  ```python
  # In USearchBackend after indexing:
  self._set_index_info("index_version", self.index_version)
  self._set_index_info("created_time", datetime.now(timezone.utc).isoformat())
  ```

- [ ] **10.3** `get_index_metadata()` returns the stored version:

  ```python
  def get_index_metadata(self) -> dict[str, Any]:
      return {
          "version": self._get_index_info("index_version") or "unknown",
          "segment_count": self.get_count(),
          "created_time": self._get_index_info("created_time"),
          "backend_id": self.backend_id,
      }
  ```

### 10.2 — Version Check in CLI

- [ ] **10.4** In `build_vector_index`, check version before indexing:

  ```python
  # After backend.configure()
  try:
      index_meta = backend.get_index_metadata()
      stored_version = index_meta.get("version", "unknown")
      
      if stored_version != "unknown" and stored_version != backend.index_version:
          console.print(
              f"[yellow]Warning: Index was built with version '{stored_version}', "
              f"but current backend version is '{backend.index_version}'.[/yellow]"
          )
          console.print(
              "The index format may have changed. Consider rebuilding with --rebuild."
          )
          if not rebuild and not click.confirm("Continue anyway?"):
              raise click.Abort()
  except Exception:
      # Index doesn't exist yet — that's fine
      pass
  ```

- [ ] **10.5** Add `retrocast index vector info` command to show index status:

  ```python
  @vector.command(name="info")
  @click.option("--backend", "backend_name", default="usearch", help="Backend to query")
  @click.option("--json", "output_json", is_flag=True, help="Output as JSON")
  def index_info(backend_name, output_json):
      """Show information about the current vector index."""
      backend = get_backend(backend_name)
      backend.configure(storage_dir)
      
      meta = backend.get_index_metadata()
      
      if output_json:
          click.echo(json.dumps(meta, indent=2))
      else:
          console.print(f"[bold]Index Information ({backend.display_name})[/bold]")
          console.print(f"  Backend ID: {meta['backend_id']}")
          console.print(f"  Index Version: {meta['version']}")
          console.print(f"  Current Backend Version: {backend.index_version}")
          console.print(f"  Segment Count: {meta['segment_count']:,}")
          console.print(f"  Created: {meta['created_time'] or 'unknown'}")
          
          if meta['version'] != backend.index_version:
              console.print(
                  "\n[yellow]⚠ Index version mismatch — consider rebuilding[/yellow]"
              )
  ```

---

## Phase 11 — User Documentation

This phase creates user-facing documentation for the plugin system.

### 11.1 — User Guide

- [ ] **11.1** Create `docs/plugins/user-guide.md`:

  ```markdown
  # Using Retrocast Plugins

  Retrocast supports pluggable vector search backends through a plugin system.
  This allows you to choose the best backend for your needs.

  ## Default Backend: USearch

  By default, retrocast uses [USearch](https://github.com/unum-cloud/usearch),
  a fast and lightweight vector search engine. USearch is included in the base
  installation and requires no additional setup.

  ## Listing Available Backends

  To see which backends are installed and available:

  ```bash
  retrocast index vector backends
  ```

  ## Installing Plugins

  Install plugins using the `plugin install` command:

  ```bash
  # From PyPI
  retrocast plugin install retrocast-zvec

  # Upgrade to latest version
  retrocast plugin install -U retrocast-zvec

  # From a local directory (development)
  retrocast plugin install -e ./my-plugin
  ```

  ## Using a Backend

  Specify a backend with the `--backend` option:

  ```bash
  # Use the default (USearch)
  retrocast index vector build

  # Use ChromaDB instead
  retrocast index vector build --backend chromadb
  ```

  ## Configuring Backends

  Some backends have configurable options:

  ```bash
  # Show current configuration
  retrocast index vector configure usearch --show

  # Set options interactively
  retrocast index vector configure usearch

  # Set options non-interactively
  retrocast index vector configure usearch --set metric=l2sq
  retrocast index vector configure usearch --set embedding_model=all-mpnet-base-v2
  ```

  ## Using ChromaDB

  If you prefer ChromaDB's all-in-one approach (built-in embeddings and metadata):

  ```bash
  # Install ChromaDB support
  pip install chromadb
  # or
  uv sync --extra chromadb

  # Build index using ChromaDB
  retrocast index vector build --backend chromadb
  ```

  ## Troubleshooting

  ### Plugin won't load

  Check if the plugin failed to load:

  ```bash
  retrocast plugin list --failed
  ```

  ### Broken plugin prevents startup

  If a plugin is so broken it prevents retrocast from starting:

  ```bash
  RETROCAST_LOAD_PLUGINS='' retrocast plugin uninstall broken-plugin -y
  ```

  ### Index version mismatch

  If you see a version mismatch warning, rebuild the index:

  ```bash
  retrocast index vector build --rebuild
  ```

  ### Embedding provider not installed

  If using USearch and you see "No embedding provider configured":

  ```bash
  pip install sentence-transformers
  ```
  ```

### 11.2 — Plugin Author Guide

- [ ] **11.2** Create `docs/plugins/author-guide.md`:

  ```markdown
  # Writing a Retrocast Plugin

  This guide explains how to create a custom vector search backend for retrocast.

  ## Package Structure

  ```
  retrocast-mybackend/
  ├── pyproject.toml
  ├── README.md
  └── retrocast_mybackend/
      └── __init__.py
  ```

  ## pyproject.toml

  ```toml
  [project]
  name = "retrocast-mybackend"
  version = "0.1.0"
  dependencies = ["retrocast"]

  [project.entry-points.retrocast]
  mybackend = "retrocast_mybackend"
  ```

  ## Backend Implementation

  ```python
  # retrocast_mybackend/__init__.py
  from pathlib import Path
  from typing import Any, Iterator

  from retrocast.hookspecs import hookimpl
  from retrocast.indexer import IndexerBackend, TranscriptionSegment


  class MyBackend(IndexerBackend):
      """Custom vector search backend.
      
      IMPORTANT: Backends receive their storage_dir from the CLI layer.
      The CLI uses retrocast.appdir.get_backend_index_dir() to determine
      the appropriate platform-specific location. Do NOT call appdir
      functions from within your backend — just use the provided storage_dir.
      
      Example storage_dir values:
          macOS:   ~/Library/Application Support/net.memexponent.retrocast/indexes/mybackend/
          Linux:   ~/.local/share/net.memexponent.retrocast/indexes/mybackend/
          Windows: C:\\Users\\<user>\\AppData\\Local\\...\\indexes\\mybackend\\
      """
      
      backend_id = "mybackend"
      display_name = "My Custom Backend"
      index_version = "1.0"

      def is_available(self) -> tuple[bool, str]:
          return self.check_import("my_vector_library")

      def configure(self, storage_dir: Path, config: dict[str, Any] | None = None) -> None:
          """Configure the backend.
          
          Args:
              storage_dir: Platform-specific directory provided by the CLI layer.
                          Store all index files within this directory.
              config: Optional configuration from backends.json
          """
          try:
              import my_vector_library
          except ImportError as exc:
              raise ImportError(
                  "my_vector_library is not installed. Install with:\n"
                  "  pip install my_vector_library"
              ) from exc
          
          self.storage_dir = storage_dir
          self.config = config or {}
          # Initialize your backend — create files INSIDE storage_dir...

      def index_segments(
          self, 
          segments: Iterator[TranscriptionSegment], 
          batch_size: int = 100
      ) -> int:
          count = 0
          for segment in segments:
              # Index segment["text"] with segment["metadata"]
              count += 1
          return count

      def search(
          self, 
          query: str, 
          n_results: int = 5, 
          podcast_filter: str | None = None
      ) -> list[dict[str, Any]]:
          # Perform search and return results
          return []

      def get_count(self) -> int:
          return 0

      def reset(self) -> None:
          pass

      def get_index_metadata(self) -> dict[str, Any]:
          return {
              "version": self.index_version,
              "segment_count": self.get_count(),
              "created_time": None,
              "backend_id": self.backend_id,
          }

      def get_config_schema(self) -> dict[str, Any] | None:
          return {
              "type": "object",
              "properties": {
                  "my_option": {
                      "type": "string",
                      "default": "default_value",
                      "description": "Description of this option",
                  },
              },
          }


  @hookimpl
  def register_indexer_backends(register):
      register(MyBackend())
  ```

  ## Development Workflow

  ```bash
  # Install in editable mode
  retrocast plugin install -e .

  # Verify it's registered
  retrocast plugin list

  # Test building an index
  retrocast index vector build --backend mybackend

  # Uninstall when done
  retrocast plugin uninstall retrocast-mybackend -y
  ```

  ## Testing Your Plugin

  Create tests that don't require the full retrocast installation:

  ```python
  def test_backend_is_available():
      backend = MyBackend()
      available, reason = backend.is_available()
      assert available, reason

  def test_backend_indexes_segments():
      backend = MyBackend()
      backend.configure(Path("/tmp/test"))
      
      segments = iter([
          {"segment_id": "1", "text": "Hello world", "metadata": {}},
          {"segment_id": "2", "text": "Test segment", "metadata": {}},
      ])
      
      count = backend.index_segments(segments)
      assert count == 2
  ```
  ```

### 11.3 — Troubleshooting Guide

- [ ] **11.3** Create `docs/plugins/troubleshooting.md`:

  ```markdown
  # Plugin Troubleshooting

  ## Common Issues

  ### "No index backends are registered"

  This means no plugins are installed or loaded. Check:

  1. Is the plugin installed?
     ```bash
     retrocast plugin list --all
     ```

  2. Did the plugin fail to load?
     ```bash
     retrocast plugin list --failed
     ```

  3. Is `RETROCAST_LOAD_PLUGINS` set to exclude your plugin?
     ```bash
     echo $RETROCAST_LOAD_PLUGINS
     ```

  ### "Backend 'xyz' not found"

  The specified backend is not registered. Run:

  ```bash
  retrocast index vector backends
  ```

  to see available backends.

  ### Plugin dependency not installed

  If a backend shows "✗" in the backends list, its required library isn't installed.
  The "Available" column will show why.

  Install the required dependency:

  ```bash
  # For sentence-transformers (used by USearch)
  pip install sentence-transformers

  # For chromadb
  pip install chromadb

  # For third-party backends
  retrocast plugin install retrocast-<backend>
  ```

  ### "No embedding provider configured"

  USearch requires an embedding provider. Install sentence-transformers:

  ```bash
  pip install sentence-transformers
  ```

  Or configure an alternative provider:

  ```bash
  retrocast index vector configure usearch --set embedding_provider=openai
  ```

  (Requires `OPENAI_API_KEY` environment variable)

  ### Broken plugin prevents startup

  If retrocast won't start due to a broken plugin:

  ```bash
  # Disable all external plugins
  RETROCAST_LOAD_PLUGINS='' retrocast plugin list

  # Uninstall the broken plugin
  RETROCAST_LOAD_PLUGINS='' retrocast plugin uninstall broken-plugin -y
  ```

  ### Index version mismatch

  If you see "Index was built with version X, current is Y":

  1. Check the index info:
     ```bash
     retrocast index vector info
     ```

  2. Rebuild if needed:
     ```bash
     retrocast index vector build --rebuild
     ```

  ## Debugging

  Enable verbose logging to see plugin loading details:

  ```bash
  retrocast -v plugin list
  ```

  Check which plugins are loaded:

  ```bash
  retrocast plugin list --all --json | jq .
  ```
  ```

### 11.4 — Update README

- [ ] **11.4** Add plugins section to main `README.md`:

  ```markdown
  ## Vector Search

  Retrocast includes built-in vector search for semantic querying of transcripts
  using [USearch](https://github.com/unum-cloud/usearch).

  ```bash
  # Build the vector index (requires sentence-transformers)
  pip install sentence-transformers
  retrocast index vector build

  # Search transcripts
  retrocast index vector search "machine learning"
  ```

  ### Alternative Backends

  You can use alternative vector search backends:

  ```bash
  # List available backends
  retrocast index vector backends

  # Install ChromaDB support
  pip install chromadb
  
  # Use ChromaDB instead of USearch
  retrocast index vector build --backend chromadb
  ```

  See [Plugin User Guide](docs/plugins/user-guide.md) for more details.

  ### Writing Plugins

  Want to add support for a new vector database? See the
  [Plugin Author Guide](docs/plugins/author-guide.md).
  ```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **USearch as default backend** | Minimal dependencies, fast, simple file-based storage, permissive license |
| **Use existing `appdir.py` for storage paths** | Consistent with existing codebase pattern; platform-appropriate directories via `platformdirs`; backends don't determine their own storage |
| **CLI layer owns storage location decisions** | Backends receive `storage_dir` from CLI; keeps backends portable and testable; follows existing ChromaDB pattern in `index_commands.py` |
| **Per-backend subdirectories under `indexes/`** | Clean separation (`indexes/usearch/`, `indexes/chromadb/`); no cross-contamination; easy to reset one backend without affecting others |
| **Core owns chunking, backends own storage** | Backends are thin (vector storage + search only); core handles transcript retrieval, chunking, metadata normalization; ensures consistency across backends |
| **Single hook in V1 (`register_indexer_backends`)** | Smaller plugin surface area; `register_commands` hook deferred to V2 after backend system stabilizes |
| **Fail fast on backend ID collisions** | Two plugins registering the same `backend_id` raises `ValueError` immediately; prevents subtle bugs |
| **Own distinfo registry instead of mutating pluggy internals** | Avoid `pm._plugin_distinfo` private attribute; more robust across pluggy versions |
| **Testable `load_plugins()` via parameter** | `load_plugins(load_entrypoints=False)` for tests; `sys._called_from_test` kept as fallback |
| **In-memory DummyBackend for tests** | No vector library dependencies; enables CLI testing without heavy deps |
| Mirror llm's `plugins.py` / `hookspecs.py` split | Clear separation; familiar to contributors who know llm |
| `_loaded` guard in `load_plugins()` | Prevents double-registration across multiple CLI invocations |
| Skip entrypoint loading in tests | Avoids test pollution from locally installed plugins |
| `RETROCAST_LOAD_PLUGINS` env var | Allows CI to test specific plugin packages explicitly; enables recovery from broken plugins |
| `plugin install` / `plugin uninstall` use `runpy.run_module("pip")` | Guarantees installation into the correct retrocast environment (uv venv, pipx, plain venv) without shelling out |
| Per-plugin `try/except` in `load_plugins()` | One broken plugin does not prevent retrocast from starting; user can then uninstall it |
| Separate embedding provider abstraction | USearch doesn't include embeddings; allows swapping models without changing backend |
| SQLite metadata storage for USearch | USearch only stores vectors; metadata stored alongside in SQLite for query filtering |
| Soft import of chromadb in optional plugin | Users without `chromadb` extras get a clear install hint, not a crash |
| `retrocast-<backend>` package naming convention | Makes plugin packages easy to discover on PyPI; mirrors llm's `llm-<name>` convention |
| Example skeleton plugin in `examples/` | Lowers the barrier for third-party backend authors; documents the full dev → publish loop |
| **Iterator-based `index_segments()` API** | Decouples backends from Datastore — backends never touch SQL; easier to test in isolation |
| **`is_available()` with `check_import()` helper** | Clear contract for availability checking without side effects; helper reduces boilerplate |
| **`get_failed_plugins()` tracking** | Failed plugins are logged and queryable, not silently ignored |
| **Index versioning with `index_version` attribute** | Detect incompatible index format changes and prompt for rebuild |
| **Configuration management with JSON schema** | Backend-specific settings persist across invocations; schema enables validation and interactive prompts |

---

## File Summary

| File | Status | Action |
|---|---|---|
| `src/retrocast/appdir.py` | Existing | Update: add `get_index_dir()`, `get_backend_index_dir()`, `get_backends_config_path()` helpers |
| `src/retrocast/hookspecs.py` | New | Create |
| `src/retrocast/plugins.py` | New | Create (includes `RETROCAST_LOAD_PLUGINS` logic, per-plugin error handling, `get_failed_plugins()`) |
| `src/retrocast/indexer.py` | New | Create (includes `TranscriptionSegment`, `IndexerBackend` with `is_available()`, `check_import()`, `index_version`) |
| `src/retrocast/embeddings.py` | New | Create (embedding provider abstraction for USearch) |
| `src/retrocast/backend_config.py` | New | Create (configuration loading/saving/validation; uses `get_backends_config_path()`) |
| `src/retrocast/default_plugins/__init__.py` | New | Create |
| `src/retrocast/default_plugins/usearch_backend.py` | New | Create (DEFAULT backend with metadata SQLite) |
| `src/retrocast/default_plugins/chromadb_backend.py` | New | Create (optional, backwards compat) |
| `src/retrocast/datastore.py` | Existing | Add `iter_transcription_segments()` method |
| `src/retrocast/index/manager.py` | Existing | Refactor → shim → eventually remove |
| `src/retrocast/index_commands.py` | Existing | Refactor (use plugin system, default `--backend usearch`) |
| `src/retrocast/plugin_commands.py` | New | Create (`plugin list`, `plugin install`, `plugin uninstall`) |
| `pyproject.toml` | Existing | Add `pluggy`, `usearch` to deps; move `chromadb` to optional; add `embeddings` optional group |
| `tests/conftest.py` | New | Create with `sys._called_from_test` sentinel and fixtures |
| `tests/fixtures/test_plugins/dummy_backend.py` | New | Create (test fixture backend) |
| `tests/fixtures/test_plugins/broken_backend.py` | New | Create (test fixture for error handling) |
| `tests/fixtures/test_plugins/unavailable_backend.py` | New | Create (test fixture for UI) |
| `tests/test_plugins.py` | New | Create (idempotency, `get_plugins`, register hooks, broken plugin handling) |
| `tests/test_index_commands.py` | New/Existing | Create/extend (mock backend, `backends` sub-command, bad `--backend`) |
| `tests/test_plugin_install.py` | New | Create (mock `runpy.run_module`, verify `sys.argv` construction) |
| `tests/integration/test_usearch_backend.py` | New | Create (full workflow with real USearch) |
| `tests/integration/test_chromadb_backend.py` | New | Create (full workflow with real ChromaDB) |
| `examples/retrocast-zvec-example/pyproject.toml` | New | Skeleton plugin package manifest |
| `examples/retrocast-zvec-example/retrocast_zvec/__init__.py` | New | Stub `ZvecBackend` + `@hookimpl` |
| `examples/retrocast-zvec-example/README.md` | New | Full dev-loop documentation |
| `docs/plugins/user-guide.md` | New | Create (user documentation) |
| `docs/plugins/author-guide.md` | New | Create (plugin author tutorial) |
| `docs/plugins/troubleshooting.md` | New | Create (troubleshooting guide) |
| `AGENTS.md` | Existing | Update (new modules, `plugin` group, `RETROCAST_LOAD_PLUGINS`, naming convention, USearch default) |
| `README.md` | Existing | Add vector search and plugins section |

---

## Migration Guide (ChromaDB → USearch)

For existing users who have ChromaDB indexes:

1. **Install dependencies for USearch embeddings:**
   ```bash
   pip install sentence-transformers
   ```

2. **Check current index:**
   ```bash
   retrocast index vector info --backend chromadb
   ```

3. **Build new USearch index:**
   ```bash
   retrocast index vector build --backend usearch
   ```

4. **Optionally keep ChromaDB available:**
   ```bash
   pip install chromadb
   # ChromaDB backend will be auto-detected and registered
   ```

5. **To continue using ChromaDB (no migration needed):**
   ```bash
   retrocast index vector build --backend chromadb
   retrocast index vector search --backend chromadb "query"
   ```

Both backends can coexist — they use separate storage directories.
