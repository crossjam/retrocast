# transcribe - Manage Audio Transcriptions

The `transcribe` command group applies ASR and provides transcription workflows.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcribe", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe [OPTIONS] COMMAND [ARGS]...                                                                                                                                                      
                                                                                                                                                                                                        
 Manage audio transcriptions (create, search, analyze).                                                                                                                                                 
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+--------------------------------------------------------------------------------------------------+
| backends  Manage transcription backends.                                                         |
| episodes  Manage and view transcribed episodes.                                                  |
| podcasts  Manage and view transcribed podcasts.                                                  |
| process   Process audio files to create transcriptions.                                          |
| search    Search transcribed podcast content.                                                    |
| summary   Display overall transcription statistics.                                              |
| validate  Validate all JSON transcription files in the app directory.                            |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->
