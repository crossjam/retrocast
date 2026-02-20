## Overview

This document describes the shape of a feature we’d like to add to
retrocast. The next task is to create a plan that designs an
architecture for the feature and steps for implementation. 

The plan should be written into the ./plans directory in markdown
format with markdown checklists to track progress.

***DO NOT WRITE ANY CODE. JUST GENERATE THE MARKDOWN PLAN.**

## Pluggable vector search / indexing backends with pluggy

I'd like to experiment with multiple different vector search libraries
such as zvec, chromadb, and usearch for indexing the transcript
content in retrocast.

It should be possible to use the Python
[pluggy](https://pluggy.readthedocs.io/en/stable/) library to
implement pluggable framework to integrate particular engines. This
should follow the model in Simon Willison's llm library 

Here's what his documentation says about
[plugins](https://llm.datasette.io/en/stable/plugins/index.html#plugins) 
```
LLM plugins can enhance LLM by making alternative Large Language
Models available, either via API or by running the models locally on
your machine. 

Plugins can also add new commands to the llm CLI tool.
```

The [overview of plugin
hooks](https://llm.datasette.io/en/stable/plugins/plugin-hooks.html)
provides an example design. 

Here's the source code for [the llm plugin
module](https://raw.githubusercontent.com/simonw/llm/refs/heads/main/llm/plugins.py) 

You can also check out the llm code repository at
https://github.com/llm/ into a temporary directory under /tmp, read
and study the code to come up with a good approach.

The feature should also consider adding a top level CLI group `plugin` for
managing installed plugins.

