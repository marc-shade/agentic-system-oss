// Presentation Template (Polylux)
// --------------------------------
// Clean, professional slide deck

#import "@preview/polylux:0.3.1": *

#set page(paper: "presentation-16-9")
#set text(font: "New Computer Modern Sans", size: 22pt)

// Theme colors
#let primary = rgb("#2563eb")
#let secondary = rgb("#64748b")
#let accent = rgb("#f59e0b")

// Custom slide styling
#let title-slide(title, subtitle: none, author: none, date: none) = {
  polylux-slide[
    #set page(fill: primary)
    #set text(fill: white)
    #align(center + horizon)[
      #text(size: 48pt, weight: "bold")[#title]

      #if subtitle != none [
        #v(0.5em)
        #text(size: 28pt)[#subtitle]
      ]

      #if author != none [
        #v(2em)
        #text(size: 24pt)[#author]
      ]

      #if date != none [
        #v(0.5em)
        #text(size: 18pt, fill: white.transparentize(30%))[#date]
      ]
    ]
  ]
}

#let section-slide(title) = {
  polylux-slide[
    #set page(fill: secondary)
    #set text(fill: white)
    #align(center + horizon)[
      #text(size: 44pt, weight: "bold")[#title]
    ]
  ]
}

#let content-slide(title, body) = {
  polylux-slide[
    #set text(fill: black)

    // Header
    #block(
      width: 100%,
      inset: (x: 1em, y: 0.5em),
      fill: primary.lighten(90%),
    )[
      #text(size: 32pt, weight: "bold", fill: primary)[#title]
    ]

    #v(1em)

    // Content
    #pad(x: 2em)[
      #body
    ]
  ]
}

// Title Slide
#title-slide(
  "{{ title }}",
  subtitle: "{{ subtitle }}",
  author: "{{ author }}",
  date: "{{ date }}"
)

// Outline
#content-slide("Outline")[
  #set text(size: 26pt)

  + Introduction
  + Background
  + Methodology
  + Results
  + Conclusion
]

// Section: Introduction
#section-slide("Introduction")

#content-slide("Motivation")[
  - Problem statement
  - Why this matters
  - Current challenges

  #v(1em)

  #align(center)[
    #block(
      fill: accent.lighten(80%),
      inset: 1em,
      radius: 8pt,
    )[
      *Key insight:* Important observation here
    ]
  ]
]

#content-slide("Our Contribution")[
  #set text(size: 24pt)

  We present a novel approach that:

  #v(0.5em)

  #grid(
    columns: (1fr, 1fr),
    gutter: 1em,
    [
      #block(fill: primary.lighten(90%), inset: 1em, radius: 4pt)[
        *Fast*

        10x speedup
      ]
    ],
    [
      #block(fill: primary.lighten(90%), inset: 1em, radius: 4pt)[
        *Accurate*

        95% precision
      ]
    ],
  )
]

// Section: Background
#section-slide("Background")

#content-slide("Related Work")[
  Previous approaches:

  - Method A: Description (Limitation)
  - Method B: Description (Limitation)
  - Method C: Description (Limitation)

  #v(1em)

  *Our approach addresses these limitations.*
]

// Section: Methodology
#section-slide("Methodology")

#content-slide("Proposed Method")[
  #grid(
    columns: (1fr, 1fr),
    gutter: 2em,
    [
      *Step 1:* Preprocessing

      *Step 2:* Feature extraction

      *Step 3:* Model training

      *Step 4:* Evaluation
    ],
    [
      #align(center)[
        #rect(
          width: 100%,
          height: 6cm,
          fill: luma(240),
          radius: 4pt,
        )[
          #align(center + horizon)[
            Diagram
          ]
        ]
      ]
    ]
  )
]

// Section: Results
#section-slide("Results")

#content-slide("Performance Comparison")[
  #table(
    columns: (1fr, auto, auto, auto),
    inset: 10pt,
    align: (left, center, center, center),
    stroke: none,
    fill: (_, y) => if y == 0 { primary.lighten(80%) } else if calc.odd(y) { luma(245) },

    [*Method*], [*Accuracy*], [*Speed*], [*Memory*],
    [Baseline], [82%], [1.0x], [4GB],
    [Improved], [88%], [1.5x], [3GB],
    [*Ours*], [*95%*], [*2.0x*], [*2GB*],
  )
]

#content-slide("Key Findings")[
  #set text(size: 24pt)

  #block(fill: accent.lighten(85%), inset: 1em, radius: 8pt, width: 100%)[
    #text(size: 28pt, weight: "bold")[Finding 1]

    Description of the first major finding.
  ]

  #v(0.5em)

  #block(fill: accent.lighten(85%), inset: 1em, radius: 8pt, width: 100%)[
    #text(size: 28pt, weight: "bold")[Finding 2]

    Description of the second major finding.
  ]
]

// Section: Conclusion
#section-slide("Conclusion")

#content-slide("Summary")[
  *We presented:*
  - Novel approach for the problem
  - Significant improvements over baselines
  - Practical implications

  #v(1em)

  *Future work:*
  - Extension A
  - Extension B
]

// Thank you slide
#polylux-slide[
  #set page(fill: primary)
  #set text(fill: white)
  #align(center + horizon)[
    #text(size: 48pt, weight: "bold")[Thank You!]

    #v(2em)

    #text(size: 24pt)[Questions?]

    #v(2em)

    #text(size: 18pt)[
      {{ author }}
      #linebreak()
      {{ email }}
    ]
  ]
]
