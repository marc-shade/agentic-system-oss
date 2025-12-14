// Invoice Template
// -----------------
// Professional billing document

#set page(paper: "us-letter", margin: 0.75in)
#set text(font: "New Computer Modern Sans", size: 10pt)

// Colors
#let primary = rgb("#1e40af")
#let secondary = rgb("#64748b")

// Header
#grid(
  columns: (1fr, 1fr),
  gutter: 2em,
  [
    // Company logo placeholder and name
    #block(fill: primary, inset: 8pt, radius: 4pt)[
      #text(fill: white, weight: "bold", size: 16pt)[{{ company_name }}]
    ]

    #v(0.5em)

    #text(fill: secondary, size: 9pt)[
      {{ company_address_line1 }} \
      {{ company_address_line2 }} \
      {{ company_email }} \
      {{ company_phone }}
    ]
  ],
  align(right)[
    #text(size: 28pt, weight: "bold", fill: primary)[INVOICE]

    #v(0.5em)

    #table(
      columns: (auto, auto),
      stroke: none,
      inset: 4pt,
      align: (right, left),

      [*Invoice #:*], [{{ invoice_number }}],
      [*Date:*], [{{ invoice_date }}],
      [*Due Date:*], [{{ due_date }}],
      [*PO #:*], [{{ po_number }}],
    )
  ]
)

#v(1.5em)

#line(length: 100%, stroke: 1pt + secondary.lighten(50%))

#v(1em)

// Bill To / Ship To
#grid(
  columns: (1fr, 1fr),
  gutter: 2em,
  [
    #text(weight: "bold", fill: primary)[BILL TO]

    #v(0.5em)

    {{ client_name }} \
    {{ client_company }} \
    {{ client_address_line1 }} \
    {{ client_address_line2 }} \
    {{ client_email }}
  ],
  [
    #text(weight: "bold", fill: primary)[SHIP TO]

    #v(0.5em)

    #if "{{ ship_to_name }}" != "" [
      {{ ship_to_name }} \
      {{ ship_to_address_line1 }} \
      {{ ship_to_address_line2 }}
    ] else [
      Same as billing address
    ]
  ]
)

#v(1.5em)

// Line items table
#table(
  columns: (auto, 1fr, auto, auto, auto),
  inset: 10pt,
  align: (center, left, center, right, right),
  stroke: none,
  fill: (_, y) => if y == 0 { primary } else if calc.odd(y) { luma(248) },

  // Header row
  text(fill: white, weight: "bold")[#],
  text(fill: white, weight: "bold")[Description],
  text(fill: white, weight: "bold")[Qty],
  text(fill: white, weight: "bold")[Rate],
  text(fill: white, weight: "bold")[Amount],

  // Line items (example - replace with actual items)
  [1], [{{ item_1_description }}], [{{ item_1_qty }}], [\${{ item_1_rate }}], [\${{ item_1_amount }}],
  [2], [{{ item_2_description }}], [{{ item_2_qty }}], [\${{ item_2_rate }}], [\${{ item_2_amount }}],
  [3], [{{ item_3_description }}], [{{ item_3_qty }}], [\${{ item_3_rate }}], [\${{ item_3_amount }}],
)

#v(1em)

// Totals
#align(right)[
  #box(width: 40%)[
    #table(
      columns: (1fr, auto),
      stroke: none,
      inset: 8pt,
      align: (left, right),

      [Subtotal], [\${{ subtotal }}],
      [Tax ({{ tax_rate }}%)], [\${{ tax_amount }}],
      [Shipping], [\${{ shipping }}],

      table.hline(stroke: 2pt + primary),

      text(weight: "bold", size: 12pt)[Total Due],
      text(weight: "bold", size: 12pt, fill: primary)[\${{ total }}],
    )
  ]
]

#v(2em)

// Payment information
#block(fill: luma(245), inset: 12pt, radius: 4pt, width: 100%)[
  #text(weight: "bold", fill: primary)[Payment Information]

  #v(0.5em)

  #grid(
    columns: (1fr, 1fr),
    gutter: 2em,
    [
      *Bank Transfer:* \
      Bank: {{ bank_name }} \
      Account: {{ account_number }} \
      Routing: {{ routing_number }}
    ],
    [
      *Other Methods:* \
      {{ payment_methods }}
    ]
  )
]

#v(1em)

// Terms and Notes
#text(size: 9pt, fill: secondary)[
  *Terms & Conditions:* {{ terms }}

  #v(0.5em)

  *Notes:* {{ notes }}
]

#v(2em)

// Footer
#align(center)[
  #text(size: 9pt, fill: secondary)[
    Thank you for your business!
  ]
]
