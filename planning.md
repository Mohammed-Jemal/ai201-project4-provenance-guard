### GOAL:
* *The goal of this project is to build an ai content attribution system that helps distinguish between  human written and ai generated content. Instead of making a simple yes/no decision, the system will analyze multiple characteristics of a piece of writting and provide confidence score that reflects how certai the prediction is.

As AI generated contents becomes more common, it is becomming increasingly difficult to identify whethe the piece of content was created by AI or human.This project aim to provide a fair and transparent way to estimate the origin of a text while acknowledging that no dictator is perfectly accurate.

* *Project overview
User will submit a pice of text such as poam, blog post or short story excerpt through an API endpoint.

The system will process the text with multiple detection signals, then each signal examine a different aspect of the writting and produce score. these score will then combined in to a final confidence score to stimate whether the content is likely written by human or AI model.

The final output bassed on the score looks like this:
1. Likely human written
2. Likely AI model written
3. Uncertain

This aproach allows the sytem to communicate uncertainity instead of  overstating confidence.


* *The ditaction signal:
To build the multi signal detaction pipeline, we will use three different signals that analyize both the structural mechanism and the semantic quality of the text.
* * signal1: Stylometric Heuristics(sentence length variance):
    . what it measure: it measures the statistical in sentence length from the text.
    .Reason: AI model tend to generate sentences with highly uniform length and structure to maximize readablity, but humans exhibit naturally mixing  very short sentence with long complex sentence.
    .Blindspot: Very short texts(like a 2 sentence poam) where variance cannot be mathematically sustained or calculated.

* *Signal2:Stylometric Heuristics(Vocabulary diversity)
    * What it measures: The ration of unique words(types) to total words(tokens) in the text.
    * Reason:Large language models optimize for predictable token path, often leading to repeatitive vocabulary structure, but humans often use more volatile, diverse and unpredictable vocabulary.
    * blindspot: Highly technical, academic, or legal human writing, which naturally requires repeating specific domain terminology, making it look artificially uniform.

* * Signal3: LLM Semantic Analysis(using groq)
    * What it measure: Semantic, contextual and structural coherance hollistically using  an LLM evaluator.
    * Reason: Evaluats the presence of common AI cliches, overly defencive structure or perfectly predictable transitional phrases that simple statistical heuristics complettly miss.
    * Blindspot: heavily edited AI generated text or highly polished human prose that reads formally.

## Signal combination and weight:
* Each signal will output a raw score between 0(likely human)-1(likely AI model). they will be combined using an ensemble weighted average.

Final_Score = (0.2*Sentence_Variance) + (0.2* Vocabulary_Diversity) + (0.6 * Groq_LLM)
*Note:the weight of LLM is higher b/c it captures semantic context that simple python calculation cannot do it.

* The consolidated score (0.0 to 1.0) maps into three specific confidence tiers designed to handle the critical asymetry of classification(minimizing false positive where human creativivity is flaged as AI generated(which is more dangerous)).

* * score <0.4 is likely human written
* * 0.4<= score <= 0.65 unsertain(leave for human review)
* * score > 0.6 likely AI model 

## Transparency Label Design
This labels will be returned to the client application to translate technical scores into plain, fail language for non-techinical users

    * * Variant A (High-Confidence Human):"Verified Authentic: This content exhibits strong characteristics of original human writing."
    * * Variant B(Uncertain): "Context Unclear =>This text contains a mix of structural signals. Our automated system cannot determine its origin.
    * *Variant C(High Confidence AI):Automated geneatation likely, the text structure looks a machine learning generated.

## Appeal workflow
When the creator fells their work has been missclassified(especially on the boraderline or false positive scenarios):
    A. Submission: The creator submits a post request to appeal containing a content_id and a written string of the creater reasoning.
    B. State change:The database/log  entry updates the submission status field from classied to "under_review".
    C. Audit Trail: The appeal details and timestamp are appended onto the structured audit log.
    D. Review dashboard Capability: A human administrator accessing the logs will filter for any entries marked "Under_review" to make a final human manual determination.

## Architectur Diagram

POST => [Heuristic calculator] ===> [Sentence length variance score]...
=>[Groq API connection] ===> [LLM evaluation score] ===> [Ensemble scoring Engine] => [Generat label & build unique ID] => [write to Audit log] => [Json Response ]=> [vocabulary tracker] ===> [Type-token ration score]

POST/Apeal => [Query database/log via content_id] => [update status to Under_review] => [Append Reasoning to Log] => [Json confirmation]

## AI tool plan
Milestone 3

    * sections Provided: Detection Signals (Signal 1 & 2), Architecture Diagram.

    *Prompt Request: Generate a Flask skeleton containing a placeholder POST /submit endpoint and the pure Python implementations for both stylometric metrics.

    *Verification: Run simple unit test scripts locally with sample arrays to confirm the math outputs a float between 0.0 and 1.0.

Milestone 4:
    *section provided:Detection signals(signal3) uncertaity representation and threshold
    *prompt request: write the helper function leaveraging the groq client library to evaluate the text, alongside the  mathematical weighting function combining all three outputs.
    *verification: pass the 4 explicit test texts outlined in the spec to verify the final score varies reasonably between random, messy text and client AI mdoel text.

Milestone 5:
    *section provided: Transparency label Design, Appeal workflow.
    *prompt request:implement the complete mapping logic for labels, the  POST/Appeal endpoint functionality, and integrate Flask-limiter onto the ingestion path.
    *verification:perform automated curl tests checking for 429 too many requests status codes when we enter the endpoint and confirm an apeal properly edits the target log.
