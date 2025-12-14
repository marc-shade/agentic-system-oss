// Technical Report Template
// -------------------------
// Professional technical documentation with code samples, figures, and tables

#set document(title: "{{ title }}", author: "{{ author }}")
#set page(
  paper: "us-letter",
  margin: (top: 1in, bottom: 1in, left: 1.25in, right: 1in),
  header: context {
    if counter(page).get().first() > 1 [
      #set text(size: 9pt, fill: gray)
      {{ title }}
      #h(1fr)
      #counter(page).display()
    ]
  },
  footer: context {
    if counter(page).get().first() > 1 [
      #set text(size: 8pt, fill: gray)
      #align(center)[{{ author }} | {{ date }}]
    ]
  }
)

#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true)
#show raw: set text(font: "Fira Code", size: 9pt)

// Title Page
#page[
  #align(center + horizon)[
    #text(size: 32pt, weight: "bold")[{{ title }}]

    #v(1em)

    #text(size: 14pt, fill: gray)[Technical Report]

    #v(3em)

    #text(size: 14pt)[{{ author }}]

    #v(0.5em)

    #text(size: 12pt, fill: gray)[{{ organization }}]

    #v(2em)

    #text(size: 11pt)[{{ date }}]

    #v(1em)

    #text(size: 10pt, fill: gray)[Version {{ version }}]
  ]
]

// Table of Contents
#outline(title: "Contents", indent: auto)

#pagebreak()

// Document begins
= Executive Summary

{{ executive_summary }}

= Introduction

== Background

Background information for this technical report.

== Objectives

The objectives of this analysis are:

+ First objective
+ Second objective
+ Third objective

== Scope

This report covers the following areas:

- Area one
- Area two
- Area three

= Technical Analysis

== System Overview

#figure(
  rect(width: 80%, height: 4cm, fill: luma(240))[
    #align(center + horizon)[System Diagram Placeholder]
  ],
  caption: [System architecture overview]
) <fig:architecture>

As shown in @fig:architecture, the system consists of...

== Implementation Details

The implementation uses the following approach:

```python
def process_data(input_data):
    """Process input data according to specifications."""
    result = transform(input_data)
    validate(result)
    return result
```

== Performance Metrics

#figure(
  table(
    columns: (1fr, auto, auto, auto),
    inset: 8pt,
    align: (left, center, center, center),
    [*Metric*], [*Baseline*], [*Current*], [*Change*],
    [Throughput], [100 req/s], [250 req/s], [+150%],
    [Latency], [50ms], [20ms], [-60%],
    [Error Rate], [2%], [0.5%], [-75%],
  ),
  caption: [Performance comparison]
) <tbl:performance>

The metrics in @tbl:performance demonstrate significant improvements.

= Methodology

== Approach

Our methodology follows these steps:

+ Data collection and preprocessing
+ Analysis and modeling
+ Validation and testing
+ Documentation and reporting

== Tools and Technologies

The following tools were used:

/ Typst: Document preparation
/ Python: Data analysis
/ Git: Version control

= Results

== Key Findings

The analysis revealed several important findings:

#block(
  fill: luma(240),
  inset: 12pt,
  radius: 4pt,
  width: 100%
)[
  *Finding 1*: Description of the first key finding and its implications.
]

#block(
  fill: luma(240),
  inset: 12pt,
  radius: 4pt,
  width: 100%
)[
  *Finding 2*: Description of the second key finding and its implications.
]

== Data Analysis

Mathematical analysis shows:

$ f(x) = integral_0^x t^2 dif t = x^3 / 3 $

= Recommendations

Based on our analysis, we recommend:

+ *Recommendation 1*: Details of the first recommendation
+ *Recommendation 2*: Details of the second recommendation
+ *Recommendation 3*: Details of the third recommendation

= Conclusion

Summary of the technical report findings and next steps.

= Appendices

== Appendix A: Raw Data

Additional supporting data.

== Appendix B: Configuration

System configuration details.

// Optional: Bibliography
// #bibliography("refs.bib", style: "ieee")
