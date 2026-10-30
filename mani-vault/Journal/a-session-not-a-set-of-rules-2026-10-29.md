# A session, not a set of rules (2026-10-29)

`feat/identify-the-connection` is deleted. Eight commits over two days each added rules (feeling underneath, limits,
something to look at, moves, three questions, a consolidated prompt) and the replies kept the same shape: a line of
sympathy, the person's situation said back, a question. The last live run, a friend who never reaches out first, made
it plain: four questions that did not build on each other, a menu to someone who had twice said "I don't know", and
the fear underneath (that the friendship matters more to him than to his friend) never named.

What I missed for too long: the model imitates examples far more than it follows rules, and the two ChatGPT
conversations at the end of `voice.md` were twenty turns of mirror-then-question. Every rule against that shape lost
to them. The session muhammad actually wanted, Lolly's role play with manasa, was in the client docs and never in the
prompt.

So this branch starts from `feat/understand-then-help` and does a small number of things: Lolly's session is the
example; the voice describes a therapist's session (neutral, empathetic, moving toward a step they choose); the
conversation prompt holds muhammad's five principles once each; the reply answers three questions and keeps a plan
before its text; and code pushes no questions.

Still missing: a way to see the model's replies before muhammad does. Without an OpenRouter key in the cloud
workspace, every change is still judged on his live runs.
