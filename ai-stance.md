# Our stance on AI

Whenever AI comes up around a software project, the conversation usually collapses into one question: did a model write the code? We think that's the wrong place to start.

The things you probably want to know about any piece of software are older than LLMs. Does it do what the docs say? Will it treat your data the way you'd expect? Can someone fix it when it breaks? Is there a person on the other end who'll answer for it? Those questions matter whether the code was hand-typed, generated, or pulled out of a forum post from 2009.

A model can sketch things out and speed up the keyboard. It doesn't decide what a project should do or which tradeoffs are worth making. Those calls belong to the people running the project, and that's true whether or not anyone got help typing.

So instead of "was AI involved," we'd rather you ask:

- Do the maintainers actually understand what they built?
- Are the design choices defensible?
- Is somebody on the hook when things go wrong?
- Can an outsider check the claims for themselves?

Our view of AI is plain. It's a power tool. Used with attention, it makes a competent developer faster. Used carelessly, it produces output that looks fine until you read it twice. Telling the difference is the human's job.

## The short version

Like most modern dev teams, we use AI-assisted tooling for things such as code completion, docs generation, review automation and security audits. Architecture, implementation and testing decisions stay with our team. For the wider picture, see [IBM](https://www.ibm.com/solutions/ai-coding), [IBM case studies](https://www.ibm.com/case-studies/ibm-software-team) and [MIT Technology Review](https://www.technologyreview.com/2025/12/15/1128352/rise-of-ai-coding-developers-2026/).

AI-driven security auditing in particular has become an industry-standard practice. See [The Hacker News](https://thehackernews.com/2026/02/claude-opus-46-finds-500-high-severity.html) and [IBM Research](https://www.ibm.com/think/insights/chatgpt-4-exploits-87-percent-one-day-vulnerabilities).

Here's how that plays out in our work.

## Where we use AI

### Looking things up

When we run into an unfamiliar library, protocol, or chunk of someone else's codebase, AI is often the fastest way in. We'll ask it to summarise something, point at the right page in the docs, or walk through an existing implementation alongside us. It's a quicker route into knowledge that already exists somewhere. What we do with that knowledge is still on us.

### Thinking out loud

Most of the real work on a project happens before the first line of code. Working out how the pieces fit together, where complexity should live, what fails first under load. That part is mostly thinking.

AI is useful here as a sparring partner. We'll describe an approach and ask it to poke holes. Sometimes it surfaces an edge case we missed. Sometimes it offers a framing that makes a knot easier to undo. Sometimes it confidently invents something that doesn't exist. The trick is to argue with it, not to take its word.

### Writing code

Once we know what we're building, AI can help with the typing. Sometimes that's a rough first draft of a module. Sometimes it's scaffolding, sometimes glue code between layers, sometimes tests and logging. On harder problems it ends up closer to pair programming: try something, look at it together, revise, repeat.

Plenty of what gets generated stays. Plenty doesn't. Models will happily invent a function that isn't in the library you're using. They'll miss a requirement you stated two paragraphs earlier. They'll suggest a shape that fights the rest of the codebase. Every line still has to be read and owned by a person before it ships.

### Cleaning up text

For documentation, READMEs, release notes and similar written material, we use AI roughly the way you'd use a smarter spellchecker. Grammar, consistency, formatting, the occasional broken link. The ideas and the structure stay ours.

### Images and diagrams

When we use generated imagery for decoration or illustration, we treat it as exactly that, dressing rather than original creative work. If the fact that an image was generated matters for the context, we say so.

## Where we don't use AI

A few things we keep on the human side of the line.

Decisions someone has to answer for. Architectural direction, security tradeoffs, the call on whether something is good enough to release.

Code we couldn't defend on a whiteboard.


## Accountability

Whether or not a model was in the loop, the work still has to hold up. So every project we ship goes through roughly the same routine.

A human reads the change before it merges. It gets exercised, by tests or by hand, depending on what's appropriate. It's documented well enough that intended behaviour can be checked against actual behaviour. The discussion around the change happens out in the open in commits, pull requests and issues, so the reasoning lives next to the result.

If something we ship is wrong, insecure or poorly designed, we'd rather you say so publicly than be polite about it. The point of working in the open is that mistakes are in the open too.

## Checking our work

You don't have to take any of this on faith.

- The source is available. Read it.
- The history is available too. Decisions and reversals show up over time.
- Issues and pull requests show the reasoning, not just the result.
- Tests live in the repository. Run them.

If something doesn't line up, open an issue. That's what they're for.

## Why bother writing this down

None of our projects are unusual enough to need a manifesto. We're writing this because the conversation around AI in software is going to keep happening, and the defaults around it aren't great yet.

Models aren't going away, and they're going to keep getting better. More developers will use them, some quietly, some loudly, some well, some badly. Plenty of software touched by AI will be terrible. Plenty will be fine. The presence of a model in the workflow doesn't, on its own, tell you which.

What's missing is a sensible middle ground. Less hype and less performative purity, and more straight answers about what was actually done.

If you use one of our projects and want to know how AI fits into it, that's a reasonable question and you should get a reasonable answer. The other way round, careful work shouldn't be written off as slop just because a model was somewhere in the pipeline.

This page is the standard we're trying to hold ourselves to. If it nudges anyone else into writing their own version, that's a good outcome.
