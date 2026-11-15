## Gemini 4 Carbon  {% id="gemini-4-carbon" %}

{% two-column-layout %}
  {% left-column class="center-vertically" %}
  *[`gemini-4-carbon`](/docs/models/gemini-4-carbon)*

  {% /left-column %}

  {% right-column class="center-vertically right-align" %}
  {% button href="https://aistudio.google.com/prompts/new_chat?model=gemini-4-carbon" variant="ais" %}
  Try it in Google AI Studio

  {% /button %}

  {% /right-column %}

{% /two-column-layout %}

{% hr /%}

Our most capable reasoning model, built for complex software engineering, deep
mathematical and scientific problem solving, high factual accuracy, autonomous
multi-step agents, and long-decode generation up to 1M tokens.

{% callout type="note" %}
  Gemini 4 Carbon is not available on the Free tier. Every token the model processes is counted and billed, including thinking tokens and internal tool system instructions and function declarations when using grounding.

{% /callout %}

{% tabs %}
  {% tab title="Standard" %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier, per 1M tokens in USD

  ---

  * Input price
  * Not available
  * $2.00 through November 30, 2026.   
  $4.00 starting December 1, 2026.

  ---

  * Output price (including thinking tokens)
  * Not available
  * $10.00 through November 30, 2026.   
  $20.00 starting December 1, 2026.

  ---

  * Context caching price
  * Not available
  * $0.10 through November 30, 2026.   
  $0.20 starting December 1, 2026.   
  Implicit caching only (explicit caching is not supported).

  ---

  * Grounding with Google Search{% sup %}*{% /sup %}
  * Not available
  * 5,000 free search requests per month (shared across all Gemini 3 and newer models),
  then $14 per 1,000 requests (subject to a [daily cap](/docs/pricing#pricing-for-tools) of 1,500 requests per day).

  ---

  * Grounding with Google Maps
  * Not available
  * 5,000 requests per month (free, shared across all Gemini 3 and newer models), then $14 / 1,000
  search queries.

  ---

  * Used to improve our products
  * Not available
  * [No](/docs/terms)
  {% /table %}

  {% sup %}*{% /sup %} A customer-submitted request to Gemini may result in one or
    more queries to Google Search. You will be charged for each individual search
    query performed.
    

  {% /tab %}
## Gemini 2.5 Pro  {% id="gemini-2.5-pro" %}

*[`gemini-2.5-pro`](/docs/models/gemini-2.5-pro)*

{% hr /%}

{% callout type="caution" %}
  Gemini 2.5 Pro (`gemini-2.5-pro`) is
  [deprecated](/docs/deprecations#gemini-2.5-pro-models) and is no longer
  available to select in Google AI Studio. Effective December 1, 2026, all API
  requests to `gemini-2.5-pro` will automatically route to
  [Gemini 3.8 Flash (`gemini-3.8-flash`)](/docs/models/gemini-3.8-flash) and be
  billed at [Gemini 3.8 Flash rates](/docs/pricing#gemini-3.8-flash).

{% /callout %}

A Pro model which excels at coding and complex reasoning tasks.

{% tabs %}
  {% tab title="Standard" %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier, per 1M tokens in USD

  ---

  * Input price
  * Free of charge
  * $1.25, prompts <= 200k tokens    
  $2.50, prompts > 200k tokens

  ---

  * Output price (including thinking tokens)
  * Free of charge
  * $10.00, prompts <= 200k tokens    
  $15.00, prompts > 200k

  ---

  * Context caching price
  * Not available
  * $0.125, prompts <= 200k tokens    
  $0.25, prompts > 200k    
  $4.50 / 1,000,000 tokens per hour (storage price)

  ---

  * Grounding with Google Search
  * Not available
  * 1,500 RPD (free), then $35 / 1,000 grounded prompts

  ---

  * Grounding with Google Maps
  * Not available
  * 10,000 RPD (free), then $25 / 1,000 grounded prompts

  ---

  * Used to improve our products
  * [Yes](/docs/terms)
  * [No](/docs/terms)
  {% /table %}

  {% /tab %}
## Gemini 2.5 Flash  {% id="gemini-2.5-flash" %}

*[`gemini-2.5-flash`](/docs/models/gemini-2.5-flash)*

{% hr /%}

{% callout type="caution" %}
  Gemini 2.5 Flash (`gemini-2.5-flash`) is
  [deprecated](/docs/deprecations#gemini-2.5-flash-models) and is no longer
  available to select in Google AI Studio. Effective December 1, 2026, all API
  requests to `gemini-2.5-flash` will automatically route to
  [Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`)](/docs/models/gemini-3.5-flash-lite)
  and be billed at
  [Gemini 3.5 Flash-Lite rates](/docs/pricing#gemini-3.5-flash-lite).

{% /callout %}

Our first hybrid reasoning model which supports a 1M token context window and
has thinking budgets.

{% tabs %}
  {% tab title="Standard" %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier, per 1M tokens in USD

  ---

  * Input price
  * Free of charge
  * $0.30 (text / image / video)    
  $1.00 (audio)

  ---

  * Output price (including thinking tokens)
  * Free of charge
  * $2.50

  ---

  * Context caching price
  * Not available
  * $0.03 (text / image / video)    
  $0.1 (audio)    
  $1.00 / 1,000,000 tokens per hour (storage price)

  ---

  * Grounding with Google Search
  * Free of charge, up to 500 RPD (limit shared with Flash-Lite RPD)
  * 1,500 RPD (free, limit shared with Flash-Lite RPD), then $35 / 1,000
  grounded prompts

  ---

  * Grounding with Google Maps
  * 500 RPD
  * 1,500 RPD (free), then $25 / 1,000 grounded prompts

  ---

  * Used to improve our products
  * [Yes](/docs/terms)
  * [No](/docs/terms)
  {% /table %}

  {% /tab %}
## Gemini 2.5 Flash Preview TTS  {% id="gemini-2.5-flash-preview-tts" %}

{% two-column-layout %}
  {% left-column class="center-vertically right-align" %}
  *[`gemini-2.5-flash-preview-tts`](/docs/models/gemini-2.5-flash-preview-tts)*

  {% /left-column %}

  {% right-column %}
  {% button href="https://aistudio.google.com/generate-speech" variant="ais" %}
  Try it in Google AI Studio

  {% /button %}

  {% /right-column %}

{% /two-column-layout %}

{% hr /%}

Our 2.5 Flash text-to-speech audio model optimized for price-performant,
low-latency, controllable speech generation.

{% tabs %}
  {% tab title="Standard" %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier, per 1M tokens in USD

  ---

  * Input price
  * Free of charge
  * $0.50 (text)

  ---

  * Output price
  * Free of charge
  * $10.00 (audio)

  ---

  * Used to improve our products
  * [Yes](/docs/terms)
  * [No](/docs/terms)
  {% /table %}

  {% /tab %}
## Gemini Robotics ER 2 Preview  {% id="gemini-robotics-er-2" %}

{% two-column-layout %}
  {% left-column %}
  *[`gemini-robotics-er-2-preview`](/docs/models/gemini-robotics-er-2-preview)*

  {% /left-column %}

  {% right-column %}
  {% button class="right-align" href="https://aistudio.google.com?model=gemini-robotics-er-2-preview" variant="ais" %}
  Try it in Google AI Studio

  {% /button %}

  {% /right-column %}

{% /two-column-layout %}

{% hr /%}

Gemini Robotics ER 2, short for Gemini Robotics Embodied Reasoning 2, is a
vision-language model endpoint that enables robots to understand their environments
precisely, supporting agentic orchestration of robots, video progress
understanding, multi-robot collaboration, and advanced spatial reasoning.

{% tabs %}
  {% tab title="Standard" %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier, per 1M tokens in USD

  ---

  * Input price
  * Free of charge
  * $1.00 (text / image / video / audio) through December 31, 2026. \\
  $2.00 (text / image / video / audio) starting January 1, 2027.

  ---

  * Output price (including thinking tokens)
  * Free of charge
  * $5.00 through December 31, 2026. \\
  $10.00 starting January 1, 2027.

  ---

  * Context caching price
  * Not available
  * $0.10 through December 31, 2026. \\
  $0.20 starting January 1, 2027. \\
  $0.50 / 1,000,000 tokens per hour (storage price) through December 31, 2026. \\
  $1.00 / 1,000,000 tokens per hour (storage price) starting January 1, 2027.

  ---

  * Grounding with Google Search
  * Not available
  * 5,000 free search requests per month (shared across all Gemini 3 and newer models), then $14 per 1,000 requests (subject to a [daily cap](/docs/pricing#pricing-for-tools) of 1,500 requests per day).

  ---

  * Used to improve our products
  * [Yes](/docs/terms)
  * [No](/docs/terms)
  {% /table %}

  {% /tab %}
## [Gemma 4](https://ai.google.dev/gemma/docs/core/model_card_4) {% id="gemma-4" %}

{% hr /%}

Our lightweight, state-of the art, open model built from the same technology
that powers our Gemini models.

{% table %}
  * Feature
  * Free Tier
  * Paid Tier, per 1M tokens in USD

  ---

  * Input price
  * Free of charge
  * Not available

  ---

  * Output price
  * Free of charge
  * Not available

  ---

  * Context caching price
  * Free of charge
  * Not available

  ---

  * Context caching (storage)
  * Free of charge
  * Not available

  ---

  * Tuning price
  * Not available
  * Not available

  ---

  * Grounding with Google Search
  * Not available
  * Not available

  ---

  * Used to improve our products
  * [Yes](/docs/terms)
  * [No](/docs/terms)
{% /table %}

