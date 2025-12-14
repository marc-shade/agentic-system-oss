// Research Paper Template
// -----------------------
// Academic paper format with abstract, sections, equations, and citations

#set document(title: "{{ title }}", author: ("{{ author }}",))
#set page(
  paper: "us-letter",
  margin: (top: 1in, bottom: 1in, left: 1in, right: 1in),
  numbering: "1"
)
#set text(font: "New Computer Modern", size: 10pt)
#set heading(numbering: "1.1")
#set par(justify: true, first-line-indent: 1em)
#set math.equation(numbering: "(1)")
#show link: underline

// Title and authors
#align(center)[
  #text(size: 16pt, weight: "bold")[{{ title }}]

  #v(1.5em)

  #text(size: 11pt)[
    {{ author }}#super[1]
    #if "{{ coauthor }}" != "" [, {{ coauthor }}#super[2]]
  ]

  #v(0.5em)

  #text(size: 9pt, style: "italic")[
    #super[1]{{ affiliation }}
    #if "{{ coauthor_affiliation }}" != "" [
      #linebreak()
      #super[2]{{ coauthor_affiliation }}
    ]
  ]

  #v(0.5em)

  #text(size: 9pt)[
    #link("mailto:{{ email }}")[{{ email }}]
  ]

  #v(1.5em)
]

// Abstract
#align(center)[
  #box(width: 85%)[
    #set text(size: 9pt)
    #set par(first-line-indent: 0pt)
    #heading(outlined: false, numbering: none, text(size: 10pt, weight: "bold")[Abstract])
    #v(0.5em)
    {{ abstract }}

    #v(0.5em)

    *Keywords:* {{ keywords }}
  ]
]

#v(2em)

// Main content
= Introduction

The field of {{ field }} has seen significant advances in recent years.
This paper presents {{ contribution }}.

Our main contributions are:
- Contribution one
- Contribution two
- Contribution three

The remainder of this paper is organized as follows.
@sec:background provides background and related work.
@sec:method describes our methodology.
@sec:experiments presents experimental results.
@sec:conclusion concludes the paper.

= Background and Related Work <sec:background>

== Theoretical Foundation

Previous work has established the following key concepts.

== Related Approaches

Several approaches have been proposed for this problem @ref1 @ref2.

= Methodology <sec:method>

== Problem Formulation

We formalize the problem as follows. Given input $x in RR^n$, we seek to find:

$ argmin_theta cal(L)(f_theta (x), y) $ <eq:objective>

where $cal(L)$ is our loss function defined as:

$ cal(L)(hat(y), y) = -sum_(i=1)^n y_i log(hat(y)_i) $ <eq:loss>

== Proposed Approach

Our approach, illustrated in @eq:objective, consists of three main components.

=== Component One

Description of the first component.

=== Component Two

Description of the second component.

=== Component Three

Description of the third component.

== Algorithm

#figure(
  kind: "algorithm",
  supplement: [Algorithm],
  block(
    fill: luma(245),
    inset: 10pt,
    radius: 4pt,
    width: 100%
  )[
    *Algorithm 1:* Proposed Method
    #line(length: 100%, stroke: 0.5pt)
    *Input:* Data $X$, parameters $theta$
    *Output:* Optimized $theta^*$

    1. Initialize $theta$ randomly
    2. *while* not converged *do*
    3. #h(1em) Compute gradient $nabla cal(L)$
    4. #h(1em) Update $theta <- theta - eta nabla cal(L)$
    5. *end while*
    6. *return* $theta^*$
  ],
  caption: [The proposed optimization algorithm]
) <alg:main>

= Experiments <sec:experiments>

== Experimental Setup

=== Datasets

We evaluate on the following datasets:

#figure(
  table(
    columns: (auto, auto, auto, auto),
    inset: 8pt,
    align: (left, center, center, center),
    [*Dataset*], [*Samples*], [*Features*], [*Classes*],
    [Dataset A], [10,000], [128], [10],
    [Dataset B], [50,000], [256], [100],
    [Dataset C], [100,000], [512], [1000],
  ),
  caption: [Dataset statistics]
) <tbl:datasets>

=== Baselines

We compare against:
+ Baseline method A @ref1
+ Baseline method B @ref2
+ State-of-the-art method C @ref3

=== Implementation Details

All experiments were conducted using:
- Hardware: GPU cluster
- Framework: PyTorch
- Training: 100 epochs, batch size 64

== Results

=== Main Results

#figure(
  table(
    columns: (auto, 1fr, 1fr, 1fr),
    inset: 8pt,
    align: (left, center, center, center),
    [*Method*], [*Dataset A*], [*Dataset B*], [*Dataset C*],
    [Baseline A], [85.2], [82.1], [79.3],
    [Baseline B], [87.4], [84.5], [81.2],
    [SOTA C], [89.1], [86.3], [83.7],
    [*Ours*], [*91.3*], [*88.7*], [*86.2*],
  ),
  caption: [Comparison with baseline methods (accuracy %)]
) <tbl:results>

Our method achieves state-of-the-art results across all datasets (@tbl:results).

=== Ablation Study

We conduct ablation studies to analyze the contribution of each component.

== Discussion

The results demonstrate that our approach effectively addresses the problem.

= Conclusion <sec:conclusion>

We presented {{ method_name }}, a novel approach for {{ problem }}.
Our experiments demonstrate {{ main_finding }}.

Future work includes:
- Extension one
- Extension two
- Extension three

// Acknowledgments (optional)
#heading(outlined: false, numbering: none)[Acknowledgments]
This work was supported by {{ funding }}.

// References
#heading(outlined: false, numbering: none)[References]

#set text(size: 9pt)
#set par(first-line-indent: 0pt, hanging-indent: 1.5em)

[1] #label("ref1") First Author et al. "Paper Title." Conference, 2024.

[2] #label("ref2") Second Author et al. "Another Paper." Journal, 2023.

[3] #label("ref3") Third Author et al. "SOTA Method." Conference, 2024.
