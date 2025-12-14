// Formal Letter Template
// ----------------------
// Professional business correspondence

#set page(paper: "us-letter", margin: 1in)
#set text(font: "New Computer Modern", size: 11pt)
#set par(justify: false)

// Sender's address (right-aligned)
#align(right)[
  {{ sender_name }} \
  {{ sender_address_line1 }} \
  {{ sender_address_line2 }} \
  {{ sender_email }} \
  {{ sender_phone }}
]

#v(1em)

// Date
#align(right)[
  {{ date }}
]

#v(2em)

// Recipient's address
{{ recipient_name }} \
{{ recipient_title }} \
{{ recipient_organization }} \
{{ recipient_address_line1 }} \
{{ recipient_address_line2 }}

#v(1.5em)

// Subject line (optional)
#if "{{ subject }}" != "" [
  *Re: {{ subject }}*

  #v(1em)
]

// Salutation
Dear {{ recipient_salutation }},

#v(0.5em)

// Body paragraphs
{{ body_paragraph_1 }}

#v(0.5em)

{{ body_paragraph_2 }}

#v(0.5em)

{{ body_paragraph_3 }}

#v(1em)

// Closing
{{ closing }},

#v(3em)

// Signature
{{ sender_name }} \
{{ sender_title }}

// Enclosures (optional)
#if "{{ enclosures }}" != "" [
  #v(1em)
  *Enclosures:*
  - {{ enclosures }}
]

// CC (optional)
#if "{{ cc }}" != "" [
  #v(0.5em)
  *cc:* {{ cc }}
]
