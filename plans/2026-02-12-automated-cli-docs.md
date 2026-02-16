Our goal is to implement automated creation of documentation for the
retrocast cli. The documentation should be derived directly from the
help of the cli tools.

Create a new directory docs if it doesn’t exist.

Here's a description of how Simon Willison uses cog to update CLI documentation

https://til.simonwillison.net/python/cog-to-update-help-in-readme

And here's documentation for the cog tool

https://cog.readthedocs.io/en/latest/

The cogapp package will need to be added as a dependency.

For each first level subcommand of retrocast create an appropriately
named markdown file. In that markdown file, generate documentation for
the subcommand. In addition to comprehensively explaining suboptions
and arguments, provide examples of usage as needed.

One documentation page for each subgroup, with sections within the page for each subcommand makes sense.

Only go one level deep on subcommand groups.

Here's an example of the cog preamble from one of the [llm packages
documentation
files](https://raw.githubusercontent.com/simonw/llm/refs/heads/main/docs/openai-models.md):


```
<!-- [[[cog
from click.testing import CliRunner
from llm.cli import cli
result = CliRunner().invoke(cli, ["models", "list"])
models = [line for line in result.output.split("\n") if line.startswith("OpenAI ")]
cog.out("```\n{}\n```".format("\n".join(models)))
]]] -->
```

Add poe tasks in pyproject.toml as needed to generate updated
documentation
