# Sentinel-RAG

**A self-correcting, multi-agent RAG system with prompt-injection defense, token-cost optimization, and full execution observability.**

Sentinel-RAG answers questions over live, continuously changing data (Notion, Gmail) using a pipeline of specialized agents — a planner, retriever, synthesizer, citation verifier, and critic — that collaborate, check each other's work, and iteratively self-correct before returning an answer. Every agent decision, retry, and token spent is traced and queryable.

<!-- OPTIONAL: drag a screenshot of the trace UI or homepage into GitHub's editor to get an image URL, then paste it here -->
<!-- ![Sentinel-RAG trace view](PASTE_IMAGE_URL_HERE) -->

---

## Why this exists

Most RAG demos answer a question by retrieving some text and asking an LLM to summarize it. That approach has no way to know if its own answer is actually correct, no defense against malicious content hiding inside retrieved documents, and no visibility into what it's costing to run. Sentinel-RAG is built around a different premise: an agent that can catch and correct its own mistakes, resist adversarial input, and account for every token it spends is a fundamentally more trustworthy system than one that just generates and returns.

---

## Architecture

### Pipeline

```
memory_reader → input_guard → (blocked | planner) → retriever → chunk_guard
   → synthesizer → citation_verifier → output_guardrail → critic
   → (write_memory | retry synthesizer | unresolved)
```

Implemented as a LangGraph state machine — a graph rather than a linear chain, specifically because the retry loop (`critic → synthesizer`) requires cycles, not just sequential steps.

### Agent responsibilities

| Agent | Role |
|---|---|
| **Memory Reader** | Semantic search over long-term memory for facts relevant to the current query, carried from prior sessions |
| **Input Guard** | Prompt-injection defense on the user's query before any retrieval happens |
| **Planner** | Decomposes the query into focused sub-questions for better retrieval coverage |
| **Retriever** | Vector similarity search (pgvector) across sub-questions, with over-fetch + deduplication |
| **Chunk Guard** | Applies injection defense to *retrieved* content — live data sources are untrusted input too |
| **Synthesizer** | Generates the answer, citing the specific chunk_id behind every factual claim |
| **Citation Verifier** | Independently checks whether each cited chunk's content genuinely supports the specific claim attached to it |
| **Output Guardrail** | Redacts PII from the generated answer before it's returned |
| **Critic** | Judges the answer; approves, or rejects with a specific, actionable reason fed back into the next retry |

### The retry loop

If the Critic rejects an answer, the reason is fed directly back into the Synthesizer, which revises rather than starting over blind. This repeats up to a fixed retry limit; if still unresolved, the pipeline stops cleanly with an explanation rather than looping indefinitely or returning a low-confidence guess.

On each retry, chunks already cited in the previous attempt are compressed to a placeholder rather than resent in full — reducing token cost on retries without reducing what the model has access to.

---

## Example run
======================================================================
RUN SUMMARY
======================================================================
Run ID:        f667d37c-1262-49b3-a852-bdcae5372a44
Query:         What internships have I received and what's blocking Project Alpha?
Verdict:       approve
Retry count:   1
Blocked?:      No

======================================================================
GUARDRAILS
======================================================================
Input guard result:  {'is_injection': False, 'layer_detected': None, 'reason': 'Passed all security layers', 'exclusion_type': None, 'is_rate_limit_artifact': False, 'source': 'user_query'}
Chunk guard result:  {'has_injection': False, 'clean_chunks': [{'chunk_id': '0a5c3941-5d6d-4d78-becb-01a8d4008b35', 'document_id': '2a8ea216-a16a-4f27-981e-b853e8d286b4', 'content': 'Vansh, earn high stipend in your preferred field and location. Apply for free on Internshala &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nb sp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp; Hi Vansh,Here are some of the latest opportunities matching your preferences. Apply now! LIMITED TIME OFFER Get Internship and Job Preparation training FREE!! By enrolling in trainings at FLAT 80% OFF! Course recommended for Vansh: Full Stack Web Development with AI Government Certified Trainings Enroll Now Actively hiring Junior Manual Tester/QA Jarvis Technology & Strategy Consulting Delhi3 months₹ 20,000 /month Today Internship Apply nowActively hiring Database Analyst TSTEPS PRIVATE LIMITED Keralapuram, Andhra (Hybrid)6 months₹ 10,000 - 15,000 /month Today Internship Apply now These results are based on the preferences you have filled. You can change them here.View more internships Get our App Stay updated with latest opportunities Available on Play Store & App StoreLearn new skills to get job-readyTop 3 recommended trainings for you that will help you set your resume apartFull Stack Web Development with AIBuild modern websites using AIEnroll nowReact with AIBuild dynamic apps using AIEnroll nowCloud computing with AWSDevelop & manage cloud apps with AWSEnroll now Explore the e-learning arm of Internshala where you can learn new-age skills on your schedule! View more trainingsInternshala (Scholiverse Educare Pvt. Ltd.)901A/B, Iris Tech Park, Sector 48, Gurugram, Haryana, India - 122018Not keen on career commitments? Unsubscribe here to break up with us. Please do not reply directly to this email, as this inbox is unmonitored. For support, please visit our Help Center or email us at helpdesk@internshala.com.', 'similarity': 0.285597273278155}, {'chunk_id': 'ae17c508-ee44-47e2-9680-0cc5112936ec', 'document_id': '5ea10d2a-25de-4fa2-943e-333e73b3ee33', 'content': 'Keep track of your Google Account data vj2754108@gmail.com <!--[if !mso]><!--> <!--[if false]><!--> You\'re receiving this email because you used Sign in with Google to sign in to <https://c.gle/ACT4xYyf5T4F5UDfPDISePXc9uVhD6pCyGhD-gUvj4j-HFWnapt7HyUATgnFOBmFNE4CmsszR5ExqGchVd4Ozs3JbK8gmgek-rD6iBGKJW_omw7z>Kuro on 4 September at 19:42. This email summarises the info that you shared. There\'s nothing that you need to do right now. <!--[if !mso]><!--> <!--[if false]><!--> <!--[if false]><!--> You\'re receiving this email because you used Signin with Google to sign in to <https://c.gle/ACT4xYyf5T4F5UDfPDISePXc9uVhD6pCyGhD-gUvj4j-HFWnapt7HyUATgnFOBmFNE4CmsszR5ExqGchVd4Ozs3JbK8gmgek-rD6iBGKJW_omw7z>Kuro on 4 September at 19:42. This email summarises the info that you shared. There\'s nothing that you need to do right now. <!--[if false]><!--> Kuro received this profile info Vansh Jain Name and profile picture vj2754108@gmail.com Email address This email includes the info that you shared on 4 September at 19:42 If you want to stop using Sign in with Google with Kuro, go to your Google Account. <!--[if !mso]><!--> <!--[if false]><!--> <!--[if false]><!--> Kuro received this profile info <!--[if false]><!--> <!--[if false]><!--> <!--[if false]><!--> Vansh Jain Name and profile picture <!--[if false]><!--> <!--[if false]><!--> <!--[if false]><!--> vj2754108@gmail.com Email address <!--[if false]><!--> <!--[if false]><!--> <!--[if false]><!--> <!--[if false]><!--> <!--[if false]><!--> <!--[if false]><!--> <!--[if false]><!--> This email includes the info that you shared on 4 September at 19:42 <!--[if false]><!--> If you want to stop using Sign in with Google with Kuro, go to your Google Account. <!--[if false]><!--> <!--[if mso]> <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="https://accounts.google.com/AccountChooser?Email=vj2754108@gmail.com&continue=https%3A%2F%2Fmyaccount.google.com%2Flinkedapps%2Foverview%2FAY6rrVG8GmWUIclUmhHUUKBEgBVN5U2EIeO0kvUI04zjIc0gZGIUiko8aLIIKQp2vqsdpuX2HBMOEuvZ1SMH7Y8sglSM%2Futm_source%3De_notification%26utm_medium%3Demail_notification" style="height:48px;width:268px;v-text-anchor:middle;" arcsize="125%" stroke="false" fillcolor="#0b57d0"> <w:anchorlock/> <v:textbox inset="0px,0px,0px,0px"> <![endif]--> <https://c.gle/ACT4xYx2Bejl6q0jwOEGQdyW2r7tKkZunMyN9KHMmAy1kxR8MGiiBZkFFqKV-i0kdsfp6gz-1R5HcVrWDqmQxHky2lH4eeyjSvWqM54J_F-fcNyL6lmJuDcsLKSWoy4HmT6IKWax4A4zdx5fvMNTHXrNItdVp6xfddPAEi2DwkqYtj2HBGDE7_RMLl7t9m9_rk8_PJUYYEtTPrZqdljkqPygNYvb4w52ogEWbPAPwq6NiU3X6veOFPnEzgYT8CcS0sUDvhuYjg1FC7DZksDx2G659CL2ClRdJnj8iCrxHmYNtyzNb6rQDKhhS_ZtYbUKKLsriO0q4RtXSAzeJg1qGzvRgNWdhxWLnnMtbC3j_A9FIBkovq-l9KNKqqnlXRUUlnD6S7j_G5mjQLWwEnK0FoLHNRwZ1gf2k37hL_zTcT2QC7oULSP7QkZVT-Ruai7B9L9SOCnEQHbLsjh59uOJnt12Rgqhjwm5> Go to your Google Account Review Kuro\'s Privacy Policy andTerms of Service to understand how Kuro will process and protect your data. If you want to delete the data that you shared with Kuro, visit Kuro.Safer with Google Your Google Account protects your privacy with advanced security designed to keep your data safe <!--[if !mso]><!--> <!--[if false]><!--> Safer with Google Your Google Account protects your privacy with advanced security designed to keep your data safe You\'ve received this email to let you know about important changes to your Google Account and services. If you want to stop receiving these emails, you can <https://myaccount.google.com/communication-preferences/unsubscribe/gt/ACT4xYwgmnKxxAteX0t6XCJoSXTZzt0yFEGB5I6B4F94EDeIclnz2pgHt5Al26F0YZUgLBGO_EAjp_zXym8pArdDA_N8_gGYCSXugPdgBG9SbS0Vz9Ug-YWiU_LpTd9Is9ZDaUNFSRMoO8Qrqmsc8WAZZmmnMW945YRjgSfpsvAMoPptnLquZ69juci7GWXVPNAfBVsz-wl7brXYTzKo4aMDxstZtpmiLS8hhZA93_2bLzyqqaTqScqF6luTt0SRUOj-2d_c2UX_b4536y_MBUscVCe65MAh_7Q?utm_source=gm&utm_medium=email&auto=true>unsubscribe. Even if you unsubscribe from these emails, you\'ll continue to receive security alerts. © 2026 Google LLC 1600 Amphitheatre Parkway, Mountain View, CA 94043', 'similarity': 0.0918055651129951}, {'chunk_id': '12a4cd66-4682-4ee9-a9ba-e361689df3c7', 'document_id': 'b508f351-50bc-44eb-8344-b9b914e244fb', 'content': 'Project Alpha is currently in its second sprint. The main goal this quarter is to ship the authentication module and integrate the payment gateway. The biggest blocker right now is a delay from the third-party API provider. The deadline for this milestone is next Friday.', 'similarity': 0.0740144467962784}, {'chunk_id': '32ff743b-6dc2-4a23-b3b9-9fddcae0ae1b', 'document_id': 'a99cc63e-8fac-4018-85ea-cfcefa86e4b4', 'content': "Google We're updating our terms of service Dear Customer, You're receiving this email because you use YouTube, Google Play, Google One, or Subscribe with Google. We are updating these terms to change the Google entity that receives your payments, from Google Ireland Limited to Google Digital Inc. Your terms of service will automatically update to reflect this change shortly (on or around 5 Oct 2026). This change won't affect the way you use these services, and you don't need to take any action. You may see this change reflected in communications you receive in connection with your service, suchas receipts or transaction statements. Your current terms of service: - YouTube Paid Terms of Service<https://c.gle/ACT4xYwdt5pUz3GxtcCaFX2Oyq6OXGm91ouSREb1tfa017OWPwSdwI2gOXIPaB_XOTn2AmrNb_UTe2mRKO_D9z2PHQw_2cTN520fhNZCGVjXZi8220P5CYpklPySY_McX9yJMyNE1s9116WMPosESvu6vRp-epjQFbChGmfs-UnZ> -Google Play Terms of Service<https://c.gle/ACT4xYyTo5FTPqmAGaef3SjzK4bceeEa5C3q4sng4QPcl8lnS7aRvdR-9gxem1AlpJAqZY7LDanf_rj9kQxGxEoxg_MzFlyu75_YbJwgdJneufrkNLg49GoWw1WG8qxysVlCurqbdYT08s8fVIg5uF0w7A> - Google One Additional Terms of Service<https://c.gle/ACT4xYz-7Czxy6mxbUYXiGXnDP7KJ6gwwOqMZegJJHH92QTy0uwoWZm6ZyWnqPmn2hcuXJxtvypo0aurp5feM2SPr8pPgVQ3qz46A75ob6i_8T2nBvSb4hip1sF00-8RNrl_ehbxyXI1mKh7T4FPtupzeCzblaJK> - Subscribe with Google Additional Terms of Service<https://c.gle/ACT4xYxQ7loATtganc5iUT1Zd85ECp22XNedrHtDPDmAjF2t8_1yBZEsQhTT6YbxDEEfGnfthM6Cx3_icqOIEyWBdpo9RIl8B7N5QOL33wTH02z0qHrguWr9mqkuEVSGokYDf9pwqN5Bq97nUQbX1IOdgEs> Sincerely, The Google Payments Team ------------------------------------------------------------------------------------ Help center<https://support.google.com/paymentscenter/?p=email_home> Contact us<https://support.google.com/paymentscenter/?p=email_contact> Google LLC 1600 Amphitheatre Parkway, Mountain View, CA 94043 You have received this mandatory service announcement to update you about important changes to Google or your account. Google", 'similarity': 0.130833863516586}, {'chunk_id': '6799acb9-2656-4e70-9d2a-21a28ee07c7e', 'document_id': '1e4ed689-1744-46b6-99d3-f7b5515d795f', 'content': "But a few weeks ago, I got a surveillance expert to take me on a tourof New York City. I consider myself pretty jaded on this topic, but I was stunned by what I saw. I learned, for example, that every New York Citypolice officer has a tool on their phone that lets them look up basically everyone on the street. It's a platform that connects tens of thousandsof cameras with public databases, social media data and systems that monitor cars -- even if you drive to another state. The amount of tracking is staggering. By now, you may have heard of one surveillance company that has become the subject of intense scrutiny. It's called Flock Safety. Itdoesn't operate in New York City, which, for me, is kind of the point of my article this week: Flock is just one part of a giant surveillance machine. A whole industry is watching and recording your life every single day. Flock and other pro-surveillance advocates say their technology helpskeep the world safe, and it's worth giving up some privacy to protect the public. Others say it hurts civil liberties and makes the world more dangerous. It's one of the hottest political issues in the US right now, and it's worth forming your own opinion. Click the link below for more. Read more https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYNhlXHDQKrFZbO0xH0HJMlP27q9NAJNSgqHJU_seImg67NJ7_UUg7nMHgSt03V4u4LBqY_Kp4OcApTRESz4Sc9CNnD7NQPkjnMBw Get in touch How much privacy would you give up to help governments police the public? I'd love to hear from you. Please get in touch if you'd like to be featured in this newsletter and are happy for your full name and location to be included. Email me here MORE TECH FROM THE BBC *Sleep scores, magnesium and white noise machines: Why 'sleepmaxxing' could be making your sleep worse https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYOthYQ-_W0ziznWwhM3PxouIMraD3DDBF_FpPQuasSMeQjwYOs2WpIXCDjqQpCCnIpYkiXO87DCM1JKzFKgkd9Df8dKMdqDMx_Mg *Uber launches the UK's first robotaxis with a driver: Here's what it's like https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYPPgto7fFf0InJiyJcsCcpJSx6ASv53whfIMKVC8Eo9DQuv5xvDmYtH1FxknBoxifg2OhPo2LFGjFbMu4d0i1VjIcq_mmvF3fR9w to ride in one * 'We felt helpless': Mother and daughter's photos stolen and manipulated to sell weight loss drugs https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYQN7L3uTg7Kot9pxfV5RmV2hPcd7BHYeF9kg_0ANJ6zltosNzSlgANCROtz3xsv-DM45JTUiKpNP_Fi-oCI8xzlaQlQ4LRPi4LtA on social media https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYR3LS5xIfNdfFQ0gXtZZWrN3t23Ks-IxnmQbFShBPJDDcMyUCc8uIlhXIoZg33SCINiUiYCU1nX-hspe9mSbsce7vpRdzymVoFRw https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYSWaKc4k1VWyX9c8t3P_MSUQkbVijHsLL97Mz1na1lQSoSxk2mos_Db8t0DCtWWyE2a_qNsn7VqiZVw11wPmKysedBAm-TXY_99A https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYTRJIti_QE3hQTi423PTZVShH0OFvSAe2-h3C-WJij5RiNJ7ZTuYrYNEj6z9C73wqFDKZuKn0Gf-9VmjOJ208x9Hs6vKnOi6-Crw ON MY MIND Are self-flying planes the future? https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYUcKCwMNPi6bcRes3PQLsXzwu1uq2QwTw-cb39fIQbcq1RxrkSZd8--8MYQfD-7C7R4KkwRAdjQ0cZvy75FoXBPY7b7YfviorCWQ About a dozen self-flying planes are already being used to spray crops in Brazil. Credit: Pyka Is it a bird? Is it a plane? Kind of: it's a self-flying aircraft. Companies are racing to bring autonomous fixed-wing planes to market. Firstly, to use for crop spraying and cargo delivery. Then, they hope, for carrying passengers. Unlike electric urban air-taxis https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYVUN6IIQlQkB-MEiZG7Mvi6euNeu7l-aa0u7iDUCYKlQpGCQ4GWljf2SqSHaNCp7FZnXAh1UMnlRSvnWizkbi9R38dmtCQyDzrbg , which can rise vertically above congested roads, these planes take off down a runway and can travel further. So will they be coming to an airport near you? Numerous challenges remain, especially over interaction with air-trafficcontrol. But in a nice twist, the technology that arrives to answer these questions might end up making piloted flying safer. Zoe Corbyn has thisreport https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYWXMehshkWNREcGrpZ8tZP-bPk023xsVBFGPPVELHQaQZ-TAHdtK62Hh1erpG07yLC1gDCxDNvk9xAvsqYtmwoSoOqOEpndQUORA .Read more https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYXXtTA0dvnkioYbyIo2PfAGZ7QkCqu_ZItul2ft_HFTMmrC_wrgf0SujE5ICroWZqRgP9pTu46hXO4BJ76yIXrHB5omqf5Bs4aIQ SOMETHING DIFFERENT https://click.email.bbc.com/?qs=ABB7InYiOjEsImQiOjQ5ODl9AAYAAAAABLsXgcYYSniZywpYqC73E_2UouHTJWTOLu-sc5sYpDUx1ma2PK1Yz3-ynNQMx73Tew65mL-ivLRaUIAByhnKZRYDcXokM9IuopOD4Yi5Wg Booking.com's fake 10 Downing Street listing The UK watchdog said its researchers were able to book a bogus stay at the British prime", 'similarity': 0.112300522625446}], 'excluded_chunks': [], 'details': []}
Output guard result: {'processed_text': 'Based on the retrieved documents, you have two internship opportunities listed: a Junior Manual Tester/QA position at Jarvis Technology & Strategy Consulting in Delhi, and a Database Analyst position at TSTEPS PRIVATE LIMITED in Keralapuram, Andhra [0a5c3941-5d6d-4d78-becb-01a8d4008b35]. Project Alpha is currently blocked by a delay from a third-party API provider [12a4cd66-4682-4ee9-a9ba-e361689df3c7].', 'redaction_details': {'emails': [], 'phones': [], 'addresses': [], 'gov_ids': [], 'credit_cards': []}, 'risky_action_info': {'has_risky_action': False, 'detected_actions': [], 'details': []}, 'guardrails_applied': []}

======================================================================
PLANNING
======================================================================
  1. What internships have I received?
  2. What is blocking Project Alpha?

======================================================================
RETRIEVAL
======================================================================
Chunks retrieved: 5
  - 0a5c3941-5d6d-4d78-becb-01a8d4008b35: Vansh, earn high stipend in your preferred field and location. Apply for free on...
  - ae17c508-ee44-47e2-9680-0cc5112936ec: Keep track of your Google Account data vj2754108@gmail.com <!--[if !mso]><!--> <...
  - 12a4cd66-4682-4ee9-a9ba-e361689df3c7: Project Alpha is currently in its second sprint. The main goal this quarter is t...
  - 32ff743b-6dc2-4a23-b3b9-9fddcae0ae1b: Google We're updating our terms of service Dear Customer, You're receiving this ...
  - 6799acb9-2656-4e70-9d2a-21a28ee07c7e: But a few weeks ago, I got a surveillance expert to take me on a tour of New Yor...

======================================================================
MEMORY USED
======================================================================
Relevant memories found: 1
  - (0.703) You have two internships: Tester/QA at Jarvis Technology & Strategy Consulting, Delhi, and Database Analyst at TSTEPS PRIVATE LIMITED, Keralapuram, Andhra; Project Alpha is blocked by a third‑party API delay.

======================================================================
FINAL ANSWER
======================================================================
Based on the retrieved documents, you have two internship opportunities listed: a Junior Manual Tester/QA position at Jarvis Technology & Strategy Consulting in Delhi, and a Database Analyst position at TSTEPS PRIVATE LIMITED in Keralapuram, Andhra [0a5c3941-5d6d-4d78-becb-01a8d4008b35]. Project Alpha is currently blocked by a delay from a third-party API provider [12a4cd66-4682-4ee9-a9ba-e361689df3c7].

Cited chunks:       ['0a5c3941-5d6d-4d78-becb-01a8d4008b35', '12a4cd66-4682-4ee9-a9ba-e361689df3c7']
Citations verified: True
Critic verdict:     approve
Critic reason:      The answer directly addresses both parts of the user's question (internships received and Project Alpha blockers) using verified citations. It is clear, concise, and well-organized.

======================================================================
MEMORY WRITE
======================================================================
{
  "stored": false,
  "action": "none",
  "summary": null
}

======================================================================
FULL NODE-BY-NODE TRACE
======================================================================
INFO:httpx:HTTP Request: GET https://vlzmmssnmvrlszwmfjtb.supabase.co/rest/v1/trace_events?select=%2A&run_id=eq.f667d37c-1262-49b3-a852-bdcae5372a44&order=created_at.asc "HTTP/2 200 OK"
  [memory_reader       ] tokens=0      latency=592ms
  [input_guard         ] tokens=0      latency=485ms
  [planner             ] tokens=149    latency=626ms
  [retriever           ] tokens=0      latency=977ms
  [chunk_guard         ] tokens=0      latency=858ms
  [synthesizer         ] tokens=6347   latency=40777ms
  [citation_verifier   ] tokens=0      latency=18267ms
  [output_guardrail    ] tokens=0      latency=4ms
  [critic              ] tokens=370    latency=1789ms
  [synthesizer         ] tokens=6483   latency=53799ms
  [citation_verifier   ] tokens=0      latency=10130ms
  [output_guardrail    ] tokens=0      latency=1ms
  [critic              ] tokens=376    latency=1944ms
  [write_memory        ] tokens=0      latency=802ms

Total events:  14
Total tokens:  13725
Total latency: 131051ms (131.1s)

======================================================================
TOKEN BREAKDOWN BY AGENT ROLE
======================================================================
INFO:httpx:HTTP Request: GET https://vlzmmssnmvrlszwmfjtb.supabase.co/rest/v1/token_logs?select=%2A&run_id=eq.f667d37c-1262-49b3-a852-bdcae5372a44 "HTTP/2 200 OK"
  synthesizer           12830 tokens  (72.0%)
  retriever              4093 tokens  (23.0%)
  critic                  746 tokens  (4.2%)
  planner                 149 tokens  (0.8%)

======================================================================
FINAL RUN STATUS (from agent_runs)
======================================================================
INFO:httpx:HTTP Request: GET https://vlzmmssnmvrlszwmfjtb.supabase.co/rest/v1/agent_runs?select=%2A&id=eq.f667d37c-1262-49b3-a852-bdcae5372a44 "HTTP/2 200 OK"
Status:         resolved
Total attempts: 2
Completed at:   2026-09-21T20:56:23.066284+00:00

Done.
```

---

## Security

Retrieved content is treated as untrusted input, not just the user's own prompt — a malicious instruction embedded inside a Notion page or email thread is a real attack surface for any RAG system that blindly trusts what it retrieves.

- **Input Guard**: layered defense against prompt injection in the user's query
- **Chunk Guard**: the same defense applied to every retrieved chunk before synthesis
- **Output Guardrail**: PII redaction on the generated answer
- **Citation Verifier**: a structural defense against hallucination — catches the Synthesizer citing a chunk that doesn't actually support what it's claiming

---

## Observability & cost tracking

Every node execution is logged — input, output, tokens used, latency — regardless of whether that node calls an LLM. This makes it possible to answer, after any run:

- Which node was the bottleneck?
- How many tokens did a specific retry cost, versus the first attempt?
- Which agent role consumes the most tokens across a run?
- Did retry-compression actually reduce cost, and by how much?

A FastAPI endpoint exposes full per-run traces; a Next.js frontend renders them as an execution timeline with a token/cost breakdown by agent role.

<!-- PASTE a screenshot of the /trace/[runId] page here once styled -->

---

## Data model (Supabase / Postgres + pgvector)

| Table | Purpose |
|---|---|
| `connections` | Source credentials for live data connectors (Notion, Gmail) |
| `documents` | Raw ingested content per source |
| `chunks` | Chunked, embedded content — the retrieval unit |
| `memory_short_term` / `memory_long_term` | Session-scoped vs. persistent semantic memory, deduplicated on write |
| `agent_runs` / `agent_attempts` | Run-level and attempt-level execution records |
| `trace_events` | Full node-by-node execution log |
| `token_logs` | Per-call token usage, attributable to a specific agent role and model |
| `embedding_cache` | Content-hash-keyed cache to avoid re-embedding unchanged text |
| `eval_cases` / `eval_results` | Structured evaluation suite and results |

Vector search runs natively in Postgres via `pgvector`, chosen over a standalone vector database since retrieval needs to join against `documents`/`connections` for citation and access control, and data volume here doesn't approach the scale where a dedicated vector store would outperform an indexed Postgres column.

---

## Token and cost optimization

- **Model routing by task**: cheaper, faster models for judgment/classification tasks (planning, critique, guardrails); a larger model reserved for synthesis, where output quality matters most
- **Retry-context compression**: previously-cited chunks replaced with placeholders on retry
- **Embedding cache**: identical text is embedded once, not on every encounter
- **Retrieval deduplication**: near-duplicate chunks filtered before reaching the Synthesizer
- **Batched guardrail/verification calls**: chunk guardrail and citation verification evaluate multiple items in a single LLM call rather than one call per item

<!-- PASTE your real measured numbers here once available, e.g.:
- X% token reduction from retry-compression (measured across N runs)
- X% fewer API calls from batching (before/after)
-->

---

## Evaluation

<!-- PASTE your D25 eval results here once complete:
- Overall accuracy: X%
- Citation correctness: X%
- Retry-resolution rate: X% resolved within 3 attempts
- Average tokens/query: X
- Category breakdown: normal / adversarial / missing-data / edge-case
-->

---

## Known limitations

- **Memory deduplication is summary-level**, not fact-level — two memories with partial factual overlap but different phrasing may not be caught as duplicates
- **Output guardrail's risky-action detection is a stub** — PII redaction is implemented; broader risky-action detection is scoped as future work
- **Sequential processing, no job queue** — ingestion and query handling run synchronously
- **Citation-to-claim mapping relies on sentence-level text matching**, which can lose precision when a single sentence cites multiple chunks

---

## Stack

FastAPI · LangGraph · Groq · Supabase (Postgres + pgvector) · Next.js · sentence-transformers (local embeddings)

---

## Setup

```bash
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # or source venv/bin/activate on Mac/Linux
pip install -r requirements.txt
# Fill in .env.local with SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```
