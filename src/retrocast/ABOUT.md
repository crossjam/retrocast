## About retrocast

[Retrocast](https://github.com/crossjam/retrocast) is AI-assisted
retrospective exploration of podcast episode archives. Podcast
aficionados typically subscribe to a decent number of podcasts but
only listen to an overall small percentage of available episodes.

One part of the retrocast approach is to be able to import podcast
metadata from end user applications like
[overcast](https://overcast.fm/). [overcast-to-sqlite][1] was the
original inspiration.

Next, there’s a goal of full, comprehensive, longitudinal downloading
and archiving of podcast episodes. Then the application of
transcription software for text conversion. Feeding into full text and
vector search indexing.

Finally, this project implements conversational AI using these indices
for retrospective interaction with the podcast content.
For example, a new technology emerges as a theme across multiple
podcasts. Retrocast can answer questions like, 

- "where else in my space of episodes did this concept appear?", 
- "how long ago was the first appearance?". 
- "whatever happened to that company FooScape?".
- "which episodes did J. Random Guest appear in and what are some key
  quotes?"
- "How have the technical themes of this podcast changed over time?"

For more details run:

```
$ retrocast --help
```

[1]: https://github.com/hbmartin/overcast-to-sqlite

