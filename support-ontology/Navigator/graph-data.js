// GENERATED FILE -- do not edit.
// Source: Ontology/*.md   Regenerate: python scripts/build_graph.py
window.ONTOLOGY = {
  "generated": "2026-10-16",
  "typeOrder": [
    "Customer",
    "Product",
    "Support",
    "Engineering",
    "Knowledge"
  ],
  "nodes": [
    {
      "id": "Account",
      "file": "Ontology/Entities/Account.md",
      "type": "Customer",
      "status": "Canonical",
      "definition": "A commercial customer organization that holds one or more licenses to our products and is entitled to receive support. The Account is the unit that entitlement, licensing, regional assignment and commercial ownership all hang off. An Account is an organization, never an individual person — the people at an account are modelled as `sup:Contact`.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "Account"
        },
        {
          "context": "Salesforce",
          "term": "Account"
        },
        {
          "context": "Informal / internal speech",
          "term": "Customer"
        },
        {
          "context": "Some reporting",
          "term": "Organization, Org"
        }
      ],
      "identity": "The CRM account ID is authoritative. Where an organization exists as multiple account records across brand-specific CRM orgs, they are the same `sup:Account` only if they share a resolved parent organization ID. See `OQ-03` — account de-duplication across brand orgs is unresolved.",
      "attributes": [
        {
          "name": "accountId",
          "type": "string",
          "required": "Yes",
          "notes": "CRM primary key"
        },
        {
          "name": "accountName",
          "type": "string",
          "required": "Yes",
          "notes": "Legal or trading name"
        },
        {
          "name": "isStrategic",
          "type": "boolean",
          "required": "No",
          "notes": "Drives CSM eligibility — see C-08"
        },
        {
          "name": "accountStatus",
          "type": "enum(Active, Lapsed, Churned)",
          "required": "Yes",
          "notes": "Lapsed = no active license"
        },
        {
          "name": "createdAt",
          "type": "date",
          "required": "Yes",
          "notes": "First became a customer"
        }
      ],
      "relations": [
        {
          "property": "isLocatedIn",
          "target": "Region",
          "cardinality": "1..1",
          "inverse": "isRegionOf"
        },
        {
          "property": "hasEntitlement",
          "target": "SupportEntitlement",
          "cardinality": "1..1",
          "inverse": "entitles"
        },
        {
          "property": "holdsLicense",
          "target": "License",
          "cardinality": "0..*",
          "inverse": "isHeldBy"
        },
        {
          "property": "raises",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "belongsTo"
        },
        {
          "property": "hasSalesRep",
          "target": "SalesRepresentative",
          "cardinality": "1..1",
          "inverse": "manages"
        },
        {
          "property": "hasCSM",
          "target": "CustomerSuccessManager",
          "cardinality": "0..1",
          "inverse": "supports"
        },
        {
          "property": "hasContact",
          "target": "Contact",
          "cardinality": "0..*",
          "inverse": "worksFor"
        },
        {
          "property": "isRepresentedBy",
          "target": "Partner",
          "cardinality": "0..*",
          "inverse": "represents"
        }
      ],
      "individuals": "None. Account is a flat class; `isStrategic` and `accountStatus` carry the distinctions that might otherwise tempt us into subclassing.",
      "disjoint": "`sup:Contact` and the internal role classes. An account is an organization; it is never a person, even when the customer is a sole trader with one named contact.",
      "constraints": [
        "C-01 — every Account has exactly one Region.",
        "C-02 — every Account has exactly one SupportEntitlement.",
        "C-07 — every Account has exactly one SalesRepresentative.",
        "C-08 — an Account may only have a CSM if isStrategic is true.",
        "C-09 — an Account with accountStatus = Active must hold at least one"
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "Account record, region, ownership",
          "authoritative": "accountId, accountName, isStrategic"
        },
        {
          "system": "Licensing system",
          "supplies": "Active license set",
          "authoritative": "accountStatus (derived)"
        }
      ],
      "questions": [
        "CQ-01",
        "CQ-02",
        "CQ-03",
        "CQ-05",
        "CQ-11",
        "CQ-14",
        "CQ-19",
        "CQ-22",
        "CQ-29"
      ],
      "openQuestions": [
        "OQ-03",
        "OQ-04",
        "OQ-42"
      ],
      "search": "account a commercial customer organization that holds one or more licenses to our\nproducts and is entitled to receive support. the account is the unit that\nentitlement, licensing, regional assignment and commercial ownership all hang\noff. an account is an organization, never an individual person — the people at\nan account are modelled as  sup:contact .   context   term used  \n --- --- \n  canonical   account  \n  salesforce   account  \n  informal / internal speech   customer  \n  some reporting   organization, org   none. account is a flat class;  isstrategic  and  accountstatus  carry the\ndistinctions that might otherwise tempt us into subclassing."
    },
    {
      "id": "Contact",
      "file": "Ontology/Entities/Contact.md",
      "type": "Customer",
      "status": "Canonical",
      "definition": "An individual person at a customer account who is authorised to raise support tickets and use self-service tools. A Contact is a person in their capacity as a customer representative. Internal staff are modelled as `sup:SupportAgent`, `sup:SalesRepresentative` or `sup:CustomerSuccessManager`.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "Contact"
        },
        {
          "context": "Salesforce",
          "term": "Contact"
        },
        {
          "context": "Ticket forms",
          "term": "Requester, Reporter, Submitter"
        }
      ],
      "identity": "CRM contact ID is authoritative.",
      "attributes": [
        {
          "name": "contactId",
          "type": "string",
          "required": "Yes",
          "notes": "CRM primary key"
        },
        {
          "name": "emailAddress",
          "type": "string",
          "required": "Yes",
          "notes": "Also the join key to ticket submissions"
        },
        {
          "name": "isSupportAuthorised",
          "type": "boolean",
          "required": "Yes",
          "notes": "Whether this contact may open tickets"
        },
        {
          "name": "isPrimary",
          "type": "boolean",
          "required": "No",
          "notes": "Primary technical contact for the account"
        }
      ],
      "relations": [
        {
          "property": "worksFor",
          "target": "Account",
          "cardinality": "1..1",
          "inverse": "hasContact"
        },
        {
          "property": "submits",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "submittedBy"
        }
      ],
      "individuals": "None.",
      "disjoint": "`sup:Account` — an organization is not a person. Also disjoint with the internal role classes: a Contact acts for the customer, an agent or rep acts for us.",
      "constraints": [
        "C-15 — every Contact belongs to exactly one Account.",
        "C-16 — a Ticket's submitting Contact must belong to the Ticket's Account.",
        "C-17 — only a Contact with isSupportAuthorised = true may submit a Ticket."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "Contact record, authorisation flag",
          "authoritative": "All contact facts"
        }
      ],
      "questions": [
        "CQ-06"
      ],
      "openQuestions": [
        "OQ-01",
        "OQ-49"
      ],
      "search": "contact an individual person at a customer account who is authorised to raise support\ntickets and use self-service tools. a contact is a person in their capacity as a\ncustomer representative. internal staff are modelled as  sup:supportagent ,\n sup:salesrepresentative  or  sup:customersuccessmanager .   context   term used  \n --- --- \n  canonical   contact  \n  salesforce   contact  \n  ticket forms   requester, reporter, submitter   none."
    },
    {
      "id": "CustomerSuccessManager",
      "file": "Ontology/Entities/CustomerSuccessManager.md",
      "type": "Customer",
      "status": "Canonical",
      "definition": "An internal individual assigned to accounts considered valuable, with responsibility for adoption, retention and relationship health. Unlike the sales representative, CSM assignment is conditional — most accounts do not have one.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "CustomerSuccessManager"
        },
        {
          "context": "Everyday use",
          "term": "CSM"
        },
        {
          "context": "Salesforce",
          "term": "Customer Success Manager, Success owner"
        },
        {
          "context": "Some teams",
          "term": "TAM, Technical account manager (may be a distinct role — OQ-36)"
        }
      ],
      "identity": "The CRM user ID is authoritative.",
      "attributes": [
        {
          "name": "csmId",
          "type": "string",
          "required": "Yes",
          "notes": "CRM user ID"
        },
        {
          "name": "isActive",
          "type": "boolean",
          "required": "Yes",
          "notes": "Currently holding the role"
        }
      ],
      "relations": [
        {
          "property": "supports",
          "target": "Account",
          "cardinality": "0..*",
          "inverse": "hasCSM"
        }
      ],
      "individuals": "None.",
      "disjoint": "`sup:SupportAgent` and `sup:SalesRepresentative` — three distinct jobs. See `C-52`.",
      "constraints": [
        "C-08 — an Account may only have a CSM if isStrategic = true. This encodes",
        "C-47 — an Account has at most one CSM."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "CSM field on the account",
          "authoritative": "supports"
        },
        {
          "system": "Customer success operations",
          "supplies": "Assignment criteria and book of business",
          "authoritative": "Coverage rules"
        }
      ],
      "questions": [
        "CQ-05",
        "CQ-14",
        "CQ-22"
      ],
      "openQuestions": [
        "OQ-36",
        "OQ-37"
      ],
      "search": "customersuccessmanager an internal individual assigned to accounts considered valuable, with\nresponsibility for adoption, retention and relationship health. unlike the sales\nrepresentative, csm assignment is  conditional  — most accounts do not have\none.   context   term used  \n --- --- \n  canonical   customersuccessmanager  \n  everyday use   csm  \n  salesforce   customer success manager, success owner  \n  some teams   tam, technical account manager ( may be a distinct role —  oq-36 )   none."
    },
    {
      "id": "License",
      "file": "Ontology/Entities/License.md",
      "type": "Customer",
      "status": "Canonical",
      "definition": "A grant of the right to use a specific product, held by a specific account, for a defined period and quantity. The license is what makes a support request legitimate: an account may only raise tickets about products it is licensed for.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "License"
        },
        {
          "context": "Salesforce",
          "term": "Asset"
        },
        {
          "context": "Licensing system",
          "term": "Entitlement key, Serial"
        },
        {
          "context": "Renewals reporting",
          "term": "Subscription"
        }
      ],
      "identity": "Composite: `accountId` + `productId` + `startDate`. A renewal produces a new License instance rather than mutating the existing one, so that historical coverage questions stay answerable.",
      "attributes": [
        {
          "name": "licenseKey",
          "type": "string",
          "required": "Yes",
          "notes": "Licensing system identifier"
        },
        {
          "name": "seatCount",
          "type": "integer",
          "required": "No",
          "notes": "Null for unlimited or site licenses"
        },
        {
          "name": "startDate",
          "type": "date",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "endDate",
          "type": "date",
          "required": "No",
          "notes": "Null = perpetual"
        },
        {
          "name": "isActive",
          "type": "boolean",
          "required": "Yes",
          "notes": "Derived: endDate is null or in the future"
        },
        {
          "name": "licenseType",
          "type": "enum(Subscription, Perpetual, Trial, NFR)",
          "required": "Yes",
          "notes": ""
        }
      ],
      "relations": [
        {
          "property": "isHeldBy",
          "target": "Account",
          "cardinality": "1..1",
          "inverse": "holdsLicense"
        },
        {
          "property": "grantsAccessTo",
          "target": "Product",
          "cardinality": "1..1",
          "inverse": "isLicensedBy"
        },
        {
          "property": "isBoundTo",
          "target": "SupportEntitlement",
          "cardinality": "1..1",
          "inverse": "binds"
        }
      ],
      "individuals": "None. `licenseType` carries the distinction.",
      "disjoint": "`sup:SupportEntitlement`. A license grants product usage; an entitlement grants service level. They are routinely conflated in conversation and must not be conflated here.",
      "constraints": [
        "C-09 — an Active account holds at least one active License.",
        "C-53 — every License is bound to exactly one SupportEntitlement.",
        "C-54 — a License's entitlement should match its Account's entitlement. Soft.",
        "C-13 — endDate, when present, must be later than startDate.",
        "C-14 — a Ticket's product must be covered by an active License held by the"
      ],
      "provenance": [
        {
          "system": "Licensing system",
          "supplies": "License keys, seats, dates",
          "authoritative": "All license facts"
        },
        {
          "system": "CRM",
          "supplies": "Asset records mirrored from licensing",
          "authoritative": "Nothing — mirror only"
        }
      ],
      "questions": [
        "CQ-04",
        "CQ-09",
        "CQ-13",
        "CQ-22",
        "CQ-29"
      ],
      "openQuestions": [
        "OQ-42",
        "OQ-09",
        "OQ-10"
      ],
      "search": "license a grant of the right to use a specific product, held by a specific account, for\na defined period and quantity. the license is what makes a support request\nlegitimate: an account may only raise tickets about products it is licensed for.   context   term used  \n --- --- \n  canonical   license  \n  salesforce   asset  \n  licensing system   entitlement key, serial  \n  renewals reporting   subscription  \n\nnote the collision: salesforce uses \"entitlement\" for the  support tier , and\n\"asset\" for the license. do not let the word \"entitlement\" cross between\n sup:supportentitlement  and  sup:license . none.  licensetype  carries the distinction."
    },
    {
      "id": "Partner",
      "file": "Ontology/Entities/Partner.md",
      "type": "Customer",
      "status": "Proposed",
      "definition": "An Independent Software Vendor (ISV) or partner organization that represents one or more accounts. Partners can submit and manage support tickets on behalf of the customers they represent.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "Partner"
        },
        {
          "context": "CRM",
          "term": "Partner / ISV"
        }
      ],
      "identity": "The CRM partner ID is authoritative.",
      "attributes": [
        {
          "name": "partnerId",
          "type": "string",
          "required": "Yes",
          "notes": "CRM primary key for the partner"
        },
        {
          "name": "partnerName",
          "type": "string",
          "required": "Yes",
          "notes": "Legal or trading name of the partner"
        },
        {
          "name": "partnershipLevel",
          "type": "string",
          "required": "No",
          "notes": "E.g., Gold, Silver"
        }
      ],
      "relations": [
        {
          "property": "represents",
          "target": "Account",
          "cardinality": "0..*",
          "inverse": "isRepresentedBy"
        },
        {
          "property": "raisesOnBehalfOf",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "submittedByPartner"
        }
      ],
      "individuals": "None.",
      "disjoint": "`sup:Account`, `sup:Contact`. A partner represents an account but is not the account itself.",
      "constraints": [
        "C-57 — A Ticket raised by a Partner must belong to an Account that the Partner represents."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "Partner record and relationships",
          "authoritative": "partnerId, partnerName"
        }
      ],
      "questions": [
        "CQ-32"
      ],
      "openQuestions": [
        "OQ-49"
      ],
      "search": "partner an independent software vendor (isv) or partner organization that represents one or more accounts. partners can submit and manage support tickets on behalf of the customers they represent.   context   term used  \n --- --- \n  canonical   partner  \n  crm   partner / isv   none."
    },
    {
      "id": "Region",
      "file": "Ontology/Entities/Region.md",
      "type": "Customer",
      "status": "Canonical",
      "definition": "A geographic territory used to distribute accounts and assign commercial and support coverage. Regions determine which sales representative owns an account and which support team's working hours apply to its tickets.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "Region"
        },
        {
          "context": "Sales operations",
          "term": "Territory"
        },
        {
          "context": "Support scheduling",
          "term": "Geo, Coverage zone"
        }
      ],
      "identity": "Natural key: the region code (`EMEA`, `NA`, `APAC`, `LATAM`). Codes are stable and never reused.",
      "attributes": [
        {
          "name": "regionCode",
          "type": "string",
          "required": "Yes",
          "notes": "Short stable code"
        },
        {
          "name": "regionName",
          "type": "string",
          "required": "Yes",
          "notes": "Display name"
        },
        {
          "name": "timeZoneRange",
          "type": "string",
          "required": "No",
          "notes": "Used to derive support coverage hours"
        }
      ],
      "relations": [
        {
          "property": "isRegionOf",
          "target": "Account",
          "cardinality": "0..*",
          "inverse": "isLocatedIn"
        },
        {
          "property": "isCoveredBy",
          "target": "SalesRepresentative",
          "cardinality": "1..*",
          "inverse": "covers"
        }
      ],
      "individuals": "Flat closed set: - `EMEA` — Europe, Middle East and Africa - `NA` — North America - `APAC` — Asia Pacific - `LATAM` — Latin America",
      "disjoint": "None.",
      "constraints": [
        "C-10 — every Region has at least one SalesRepresentative covering it."
      ],
      "provenance": [
        {
          "system": "Salesforce",
          "supplies": "Territory assignment on the account",
          "authoritative": "regionCode per account"
        },
        {
          "system": "Sales operations spreadsheet",
          "supplies": "Region definitions and rep coverage",
          "authoritative": "Region set, coverage map"
        }
      ],
      "questions": [
        "CQ-01",
        "CQ-05",
        "CQ-14",
        "CQ-19"
      ],
      "openQuestions": [
        "OQ-05",
        "OQ-41"
      ],
      "search": "region a geographic territory used to distribute accounts and assign commercial and\nsupport coverage. regions determine which sales representative owns an account\nand which support team's working hours apply to its tickets.   context   term used  \n --- --- \n  canonical   region  \n  sales operations   territory  \n  support scheduling   geo, coverage zone   flat closed set:\n-  emea  — europe, middle east and africa\n-  na  — north america\n-  apac  — asia pacific\n-  latam  — latin america\n\nregions are deliberately  flat . sub-regions (dach, benelux, anz) are not\nmodelled: the support organization assigns coverage and routes tickets at the\ntop level, so a hierarchy would add traversal cost without answering a question\nanyone asks. if regional roll-ups are ever needed below this level, that is a\nnew modelling decision — see  oq-41 ."
    },
    {
      "id": "SalesRepresentative",
      "file": "Ontology/Entities/SalesRepresentative.md",
      "type": "Customer",
      "status": "Canonical",
      "definition": "An internal individual who commercially owns a set of accounts. Assignment is driven by region: an account's sales representative is drawn from the representatives covering that account's region.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "SalesRepresentative"
        },
        {
          "context": "Salesforce",
          "term": "Account owner, Owner"
        },
        {
          "context": "Sales team",
          "term": "AE, Account executive, Rep"
        },
        {
          "context": "Renewals",
          "term": "Renewal owner (may be a different person — see OQ-34)"
        }
      ],
      "identity": "The CRM user ID is authoritative.",
      "attributes": [
        {
          "name": "repId",
          "type": "string",
          "required": "Yes",
          "notes": "CRM user ID"
        },
        {
          "name": "isActive",
          "type": "boolean",
          "required": "Yes",
          "notes": "Currently holding the role"
        }
      ],
      "relations": [
        {
          "property": "manages",
          "target": "Account",
          "cardinality": "0..*",
          "inverse": "hasSalesRep"
        },
        {
          "property": "covers",
          "target": "Region",
          "cardinality": "1..*",
          "inverse": "isCoveredBy"
        }
      ],
      "individuals": "None.",
      "disjoint": "`sup:SupportAgent` and `sup:CustomerSuccessManager` — three distinct jobs. See `C-52`.",
      "constraints": [
        "C-07 — every Account has exactly one SalesRepresentative.",
        "C-10 — every Region has at least one SalesRepresentative covering it.",
        "C-46 — an Account's SalesRepresentative must cover the Account's Region."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "Account ownership",
          "authoritative": "manages"
        },
        {
          "system": "Sales operations territory model",
          "supplies": "Region coverage",
          "authoritative": "covers"
        }
      ],
      "questions": [
        "CQ-05",
        "CQ-19",
        "CQ-22"
      ],
      "openQuestions": [
        "OQ-34",
        "OQ-35"
      ],
      "search": "salesrepresentative an internal individual who commercially owns a set of accounts. assignment is\ndriven by region: an account's sales representative is drawn from the\nrepresentatives covering that account's region.   context   term used  \n --- --- \n  canonical   salesrepresentative  \n  salesforce   account owner, owner  \n  sales team   ae, account executive, rep  \n  renewals   renewal owner ( may be a different person — see  oq-34 )   none."
    },
    {
      "id": "SupportEntitlement",
      "file": "Ontology/Entities/SupportEntitlement.md",
      "type": "Customer",
      "status": "Canonical",
      "definition": "The tier of support service an account is entitled to receive. The tier governs response time targets, escalation rights and channel access. Entitlement is a property of the account, not of an individual ticket or license.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "SupportEntitlement"
        },
        {
          "context": "Most products",
          "term": "Support Level, Support Plan"
        },
        {
          "context": "Salesforce",
          "term": "Entitlement"
        },
        {
          "context": "Premium tier — most products",
          "term": "Premium Support"
        },
        {
          "context": "Premium tier — Platinum-naming products",
          "term": "Platinum Support"
        },
        {
          "context": "Standard tier",
          "term": "Standard Support, Basic (unverified)"
        }
      ],
      "identity": "Natural key: the canonical tier code (`STANDARD`, `PREMIUM`). Entitlement is a controlled vocabulary, not a per-account record — the per-account fact is the `hasEntitlement` link, and its effective dates live on the link.",
      "attributes": [
        {
          "name": "tierCode",
          "type": "enum(STANDARD, PREMIUM)",
          "required": "Yes",
          "notes": "Canonical code"
        },
        {
          "name": "tierRank",
          "type": "integer",
          "required": "Yes",
          "notes": "Higher = more entitled. Standard 1, Premium 2"
        },
        {
          "name": "grantsEscalationRight",
          "type": "boolean",
          "required": "Yes",
          "notes": "Whether the tier may demand escalation"
        },
        {
          "name": "responseTargetHours",
          "type": "integer",
          "required": "No",
          "notes": "Varies by severity — see OQ-06"
        }
      ],
      "relations": [
        {
          "property": "entitles",
          "target": "Account",
          "cardinality": "0..*",
          "inverse": "hasEntitlement"
        },
        {
          "property": "binds",
          "target": "License",
          "cardinality": "0..*",
          "inverse": "isBoundTo"
        }
      ],
      "individuals": "Closed set of two individuals:",
      "disjoint": "None — but the two individuals are mutually exclusive per account at a given time. See `C-02`.",
      "constraints": [
        "C-02 — an Account has exactly one SupportEntitlement at any point in time.",
        "C-11 — the set of tiers is closed. A value that is neither STANDARD nor",
        "C-12 — grantsEscalationRight is true only for PREMIUM.",
        "C-53 — every License is bound to exactly one SupportEntitlement.",
        "C-54 — a License's entitlement should match its Account's entitlement."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "Entitlement field on account",
          "authoritative": "Per-account tier"
        },
        {
          "system": "Support policy documentation",
          "supplies": "Tier definitions and response targets",
          "authoritative": "responseTargetHours"
        }
      ],
      "questions": [
        "CQ-02",
        "CQ-03",
        "CQ-11",
        "CQ-19",
        "CQ-23",
        "CQ-27",
        "CQ-29"
      ],
      "openQuestions": [
        "OQ-06",
        "OQ-07",
        "OQ-08",
        "OQ-42"
      ],
      "search": "supportentitlement the tier of support service an account is entitled to receive. the tier governs\nresponse time targets, escalation rights and channel access. entitlement is a\nproperty of the account, not of an individual ticket or license.\n\n this class is the primary reason the ontology exists.  the same tier is\ncalled  premium support  for most products and  platinum support  for others.\nan agent that treats those as two tiers will under-count the premium base.   context   term used  \n --- --- \n  canonical   supportentitlement  \n  most products   support level, support plan  \n  salesforce   entitlement  \n  premium tier — most products   premium support  \n  premium tier — platinum-naming products    platinum support   \n  standard tier   standard support, basic (unverified)  \n\nthe tier-value aliases are listed here as well as in the individuals table\nbelow, because \"platinum\" is the term someone is most likely to arrive with and\nit should be findable at the top of this file. see also\n 03-vocabulary-and-equivalence.md  →  eq-02 . closed set of two individuals:\n\n  canonical individual    tiercode    aliases and where they are used  \n --- --- --- \n   standard     standard    \"basic\", \"included support\" — usage unverified, see  oq-07   \n   premium     premium     \"platinum support\"  for the products that use that naming — see  sup:product.usesplatinumnaming . same tier, different label.  \n\npremium and platinum are declared  equivalent , not related. see\n 03-vocabulary-and-equivalence.md  →  eq-02 ."
    },
    {
      "id": "Product",
      "file": "Ontology/Entities/Product.md",
      "type": "Product",
      "status": "Canonical",
      "definition": "A software product that customers license and raise support tickets about. The Product is what a license grants access to, what a ticket concerns, and what documentation describes. It is the join point between the commercial, support and knowledge parts of the model.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "Product"
        },
        {
          "context": "Licensing system",
          "term": "SKU, Part number"
        },
        {
          "context": "Salesforce",
          "term": "Product2, Asset product"
        },
        {
          "context": "Support forms",
          "term": "Product, Component"
        },
        {
          "context": "KB tooling",
          "term": "Product, Product folder"
        },
        {
          "context": "Commercial reporting",
          "term": "Product line, Product family"
        }
      ],
      "identity": "The licensing system product ID is authoritative. Version is not part of identity — a product and its versions are the same product. Version-specific facts would need `sup:ProductVersion`, which is not modelled (`OQ-15`).",
      "attributes": [
        {
          "name": "productId",
          "type": "string",
          "required": "Yes",
          "notes": "Licensing system key"
        },
        {
          "name": "productName",
          "type": "string",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "currentVersion",
          "type": "string",
          "required": "No",
          "notes": "Latest generally available release"
        },
        {
          "name": "lifecycleStatus",
          "type": "enum(GA, Maintenance, EndOfLife)",
          "required": "Yes",
          "notes": "EOL drives documentation retirement"
        },
        {
          "name": "endOfLifeDate",
          "type": "date",
          "required": "No",
          "notes": "Required when lifecycleStatus = EndOfLife"
        },
        {
          "name": "usesPlatinumNaming",
          "type": "boolean",
          "required": "Yes",
          "notes": "True where Premium Support is sold as Platinum Support — alias anchor for EQ-02"
        },
        {
          "name": "severityTermUsed",
          "type": "enum(Severity, Priority)",
          "required": "Yes",
          "notes": "Which word this product's support uses — alias anchor for EQ-03"
        },
        {
          "name": "documentationRootUrl",
          "type": "string",
          "required": "No",
          "notes": "Entry point for this product's KB"
        }
      ],
      "relations": [
        {
          "property": "isLicensedBy",
          "target": "License",
          "cardinality": "0..*",
          "inverse": "grantsAccessTo"
        },
        {
          "property": "isSubjectOf",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "concerns"
        },
        {
          "property": "isDescribedBy",
          "target": "Documentation",
          "cardinality": "0..*",
          "inverse": "describes"
        },
        {
          "property": "isSupportedBy",
          "target": "SupportAgent",
          "cardinality": "0..*",
          "inverse": "specialisesIn"
        }
      ],
      "individuals": "Populated per organization from the licensing system or the KB folder structure. Placeholder examples: `ExampleAnalytics`, `ExampleDataWarehouse`, `ExampleDesigner`.",
      "disjoint": "None.",
      "constraints": [
        "C-22 — a Product with lifecycleStatus = EndOfLife must have an",
        "C-23 — documentation describing an EndOfLife product should be reviewed for",
        "C-51 — every Product declares usesPlatinumNaming and severityTermUsed."
      ],
      "provenance": [
        {
          "system": "Licensing system",
          "supplies": "Product catalogue, SKUs",
          "authoritative": "productId, productName"
        },
        {
          "system": "Product management",
          "supplies": "Lifecycle status and EOL dates",
          "authoritative": "lifecycleStatus, endOfLifeDate"
        },
        {
          "system": "Release engineering",
          "supplies": "Current version",
          "authoritative": "currentVersion"
        },
        {
          "system": "Pricing and packaging",
          "supplies": "Tier naming per product",
          "authoritative": "usesPlatinumNaming"
        },
        {
          "system": "Support policy per product",
          "supplies": "Severity field naming",
          "authoritative": "severityTermUsed"
        },
        {
          "system": "KB folder structure",
          "supplies": "Documentation grouping",
          "authoritative": "documentationRootUrl"
        }
      ],
      "questions": [
        "CQ-04",
        "CQ-07",
        "CQ-08",
        "CQ-09",
        "CQ-12",
        "CQ-13",
        "CQ-16",
        "CQ-22",
        "CQ-26"
      ],
      "openQuestions": [
        "OQ-14",
        "OQ-15",
        "OQ-44"
      ],
      "search": "product a software product that customers license and raise support tickets about. the\nproduct is what a license grants access to, what a ticket concerns, and what\ndocumentation describes. it is the join point between the commercial, support\nand knowledge parts of the model.\n\nproduct is deliberately a  single flat level . brand and product-line\nhierarchies exist commercially, but they sit outside the support organization\nand modelling them added structure without answering a support question.   context   term used  \n --- --- \n  canonical   product  \n  licensing system   sku, part number  \n  salesforce   product2, asset product  \n  support forms   product, component  \n  kb tooling   product, product folder  \n  commercial reporting   product line, product family  \n\n\"product line\" is recorded here as an  alias , not a separate class. where\nsomeone says \"product line\" in a support context they mean this class. populated per organization from the licensing system or the kb folder\nstructure. placeholder examples:  exampleanalytics ,  exampledatawarehouse ,\n exampledesigner .\n\nuse family-level names (one per kb product folder) unless the organization\nneeds sku-level granularity.\nwhether the support organization needs sku-level granularity underneath them is\n oq-14 ."
    },
    {
      "id": "CRM",
      "file": "Ontology/Entities/CRM.md",
      "type": "Support",
      "status": "Canonical",
      "definition": "A customer relationship management system that records tickets. Each distinct CRM instance is a distinct instance of this class, because each carries its own ticket numbering, its own user records, and — critically — its own vocabulary.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "CRM"
        },
        {
          "context": "CRM administration",
          "term": "Org, Instance, Tenant"
        },
        {
          "context": "Data engineering",
          "term": "Source, System of record, Upstream"
        },
        {
          "context": "Everyday use",
          "term": "Salesforce, \"the system\""
        }
      ],
      "identity": "Natural key: the system code (e.g. `SF_EMEA`, `SF_AMER`). Each org is a separate instance even when several orgs run on the same platform, because the ID spaces and the vocabulary do not carry across.",
      "attributes": [
        {
          "name": "systemCode",
          "type": "string",
          "required": "Yes",
          "notes": "Stable short code"
        },
        {
          "name": "systemName",
          "type": "string",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "ticketTermUsed",
          "type": "enum(Ticket, Case)",
          "required": "Yes",
          "notes": "The alias anchor for EQ-01"
        },
        {
          "name": "isAuthoritative",
          "type": "boolean",
          "required": "Yes",
          "notes": "Whether this system is the source of truth or a mirror"
        }
      ],
      "relations": [
        {
          "property": "records",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "recordedIn"
        }
      ],
      "individuals": "Template rows. Replace with the organization's real instances.",
      "disjoint": "All domain classes. A CRM is a system that holds facts about the organization, not a part of the organization itself.",
      "constraints": [
        "C-48 — every Ticket is recorded in exactly one CRM. This is what makes",
        "C-49 — a fact from a CRM with isAuthoritative = false must not override a",
        "C-50 — every CRM declares ticketTermUsed. A system whose vocabulary is"
      ],
      "provenance": [
        {
          "system": "Integration inventory",
          "supplies": "The list of CRM instances",
          "authoritative": "System set"
        },
        {
          "system": "CRM administration",
          "supplies": "Org configuration and field labels",
          "authoritative": "ticketTermUsed"
        },
        {
          "system": "This ontology",
          "supplies": "Trust ranking",
          "authoritative": "isAuthoritative"
        }
      ],
      "questions": [
        "CQ-07",
        "CQ-18"
      ],
      "openQuestions": [
        "OQ-38",
        "OQ-50",
        "OQ-39",
        "OQ-18"
      ],
      "search": "crm a customer relationship management system that records tickets. each distinct\ncrm instance is a distinct instance of this class, because each carries its own\nticket numbering, its own user records, and — critically — its own vocabulary.\n\nthe crm is modelled for two reasons:  identity , because ticket numbers are\nunique within a crm and not across them, and  vocabulary , because the crm is\nwhat determines whether a support request is called a ticket or a case.   context   term used  \n --- --- \n  canonical   crm  \n  crm administration   org, instance, tenant  \n  data engineering   source, system of record, upstream  \n  everyday use   salesforce, \"the system\"   template rows. replace with the organization's real instances.\n\n   systemcode     systemname     tickettermused     isauthoritative    source of this entry  \n --- --- --- --- --- \n   sf    salesforce    case    yes   example:  case  is the platform's own object name  \n   zd    zendesk    ticket    yes   example:  ticket  is the platform's own object name  \n\n tickettermused  is the alias anchor for  eq-01  and  c-50  requires every\ncrm to declare it. populate it from the platform's own object name or the\norg's field labels. mark a value  unconfirmed  rather than guessing — an alias\nmap populated from assumption is worse than one that is visibly incomplete."
    },
    {
      "id": "Escalation",
      "file": "Ontology/Entities/Escalation.md",
      "type": "Support",
      "status": "Canonical",
      "definition": "The act of a support agent referring a ticket to development because it has been identified as a defect or as a request for new functionality. The Escalation produces a Jira issue and is the only legitimate way a Jira ID becomes associated with a ticket.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "Escalation"
        },
        {
          "context": "Agent conversation",
          "term": "Bug report, Dev handoff, \"raising a Jira\""
        },
        {
          "context": "CRM",
          "term": "Escalation flag, Escalated case"
        }
      ],
      "identity": "Surrogate: generated UUID. There is no natural key — the same ticket can be escalated more than once, and the same Jira issue can receive escalations from many tickets.",
      "attributes": [
        {
          "name": "escalationId",
          "type": "uuid",
          "required": "Yes",
          "notes": "Surrogate key"
        },
        {
          "name": "escalationType",
          "type": "enum(Bug, Enhancement)",
          "required": "Yes",
          "notes": "The agent's classification"
        },
        {
          "name": "escalatedAt",
          "type": "datetime",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "justification",
          "type": "text",
          "required": "Yes",
          "notes": "Why the agent judged this a dev matter"
        },
        {
          "name": "wasAccepted",
          "type": "boolean",
          "required": "No",
          "notes": "Whether development accepted the classification"
        },
        {
          "name": "reproductionSteps",
          "type": "text",
          "required": "No",
          "notes": "Expected for Bug type"
        }
      ],
      "relations": [
        {
          "property": "originatesFrom",
          "target": "Ticket",
          "cardinality": "1..1",
          "inverse": "escalatedAs"
        },
        {
          "property": "producedIssue",
          "target": "JiraIssue",
          "cardinality": "1..1",
          "inverse": "raisedBy"
        },
        {
          "property": "escalatedBy",
          "target": "SupportAgent",
          "cardinality": "1..1",
          "inverse": "escalates"
        }
      ],
      "individuals": "None. `escalationType` carries the Bug / Enhancement distinction rather than subclassing, because the two share every property and differ only in classification — and because the classification can be corrected after the fact.",
      "disjoint": "`sup:Ticket`, `sup:JiraIssue`. The escalation is the link between them, not either end of it.",
      "constraints": [
        "C-05 — a Ticket may only carry a Jira reference through an Escalation.",
        "C-06 — a Ticket with status = Escalated has at least one open Escalation.",
        "C-27 — every Escalation produces exactly one JiraIssue, and the issue's",
        "C-28 — an Escalation of type Bug should have reproductionSteps. Advisory,",
        "C-29 — only a SupportAgent may create an Escalation."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "Escalation record on the case, agent identity",
          "authoritative": "escalatedAt, escalatedBy, justification"
        },
        {
          "system": "Jira",
          "supplies": "The resulting issue key, acceptance",
          "authoritative": "producedIssue, wasAccepted"
        }
      ],
      "questions": [
        "CQ-11",
        "CQ-15",
        "CQ-17",
        "CQ-18",
        "CQ-19",
        "CQ-23",
        "CQ-27"
      ],
      "openQuestions": [
        "OQ-21",
        "OQ-22"
      ],
      "search": "escalation the act of a support agent referring a ticket to development because it has been\nidentified as a defect or as a request for new functionality. the escalation\nproduces a jira issue and is the only legitimate way a jira id becomes\nassociated with a ticket.\n\n why this is its own class.  it would be simpler to draw a direct line from\nticket to jiraissue. but the escalation carries its own facts — who escalated,\nwhen, on what grounds, whether it was accepted, and whether the resulting issue\nwas a bug or an enhancement. those facts belong to the escalation event, not to\nthe ticket and not to the jira issue. this is a reified relationship: a\nrelationship promoted to a class because it has properties of its own.   context   term used  \n --- --- \n  canonical   escalation  \n  agent conversation   bug report, dev handoff, \"raising a jira\"  \n  crm   escalation flag, escalated case  \n\nnote: \"escalation\" is also used loosely to mean  raising a ticket's severity  or\n involving a manager . those are different actions and are  not  this class.\nsee  oq-21 . none.  escalationtype  carries the bug / enhancement distinction rather than\nsubclassing, because the two share every property and differ only in\nclassification — and because the classification can be corrected after the fact."
    },
    {
      "id": "SLA",
      "file": "Ontology/Entities/SLA.md",
      "type": "Support",
      "status": "Proposed",
      "definition": "The Service Level Agreement that governs a ticket, dictating the target times for response and resolution. An SLA is determined by the severity of the ticket and the entitlement of the customer account. Support agents are measured against their ability to meet these SLA targets.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "SLA"
        },
        {
          "context": "CRM",
          "term": "Service Level Agreement"
        },
        {
          "context": "ITSM",
          "term": "SLA"
        }
      ],
      "identity": "A composite of `severityLevel` + `entitlementTier`.",
      "attributes": [
        {
          "name": "slaName",
          "type": "string",
          "required": "Yes",
          "notes": "E.g., \"Premium S1\""
        },
        {
          "name": "targetResponseMinutes",
          "type": "integer",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "targetResolutionMinutes",
          "type": "integer",
          "required": "Yes",
          "notes": ""
        }
      ],
      "relations": [
        {
          "property": "governs",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "isGovernedBy"
        },
        {
          "property": "measures",
          "target": "SupportAgent",
          "cardinality": "0..*",
          "inverse": "measuredAgainst"
        }
      ],
      "individuals": "None.",
      "disjoint": "`sup:Ticket`, `sup:SeverityLevel`, `sup:SupportEntitlement`. An SLA is the rule, not the ticket itself or its priority.",
      "constraints": [
        "C-56 — Every Ticket has exactly one SLA, which must align with its SeverityLevel and its Account's SupportEntitlement."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "SLA matrix configuration",
          "authoritative": "targetResponseMinutes, targetResolutionMinutes"
        }
      ],
      "questions": [
        "CQ-30",
        "CQ-31"
      ],
      "openQuestions": [
        "OQ-48"
      ],
      "search": "sla the service level agreement that governs a ticket, dictating the target times for response and resolution. an sla is determined by the severity of the ticket and the entitlement of the customer account. support agents are measured against their ability to meet these sla targets.   context   term used  \n --- --- \n  canonical   sla  \n  crm   service level agreement  \n  itsm   sla   none."
    },
    {
      "id": "SeverityLevel",
      "file": "Ontology/Entities/SeverityLevel.md",
      "type": "Support",
      "status": "Canonical",
      "definition": "The graded measure of a ticket's business impact and urgency, used to set response expectations and routing. Every ticket has exactly one.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "SeverityLevel"
        },
        {
          "context": "Products using severity naming",
          "term": "Severity, Sev"
        },
        {
          "context": "Products using priority naming",
          "term": "Priority, Pri"
        },
        {
          "context": "Escalation conversations",
          "term": "Impact, Urgency (informal, not a field)"
        }
      ],
      "identity": "Natural key: the canonical level code `S1`–`S4`. All product-specific labels (`P1`, `Critical`, `High`, `1 - Urgent`) resolve to one of these four.",
      "attributes": [
        {
          "name": "levelCode",
          "type": "enum(S1, S2, S3, S4)",
          "required": "Yes",
          "notes": "Canonical code"
        },
        {
          "name": "levelRank",
          "type": "integer",
          "required": "Yes",
          "notes": "1 = most severe. Lower rank = more urgent"
        },
        {
          "name": "levelName",
          "type": "string",
          "required": "Yes",
          "notes": "Canonical display name"
        },
        {
          "name": "definition",
          "type": "text",
          "required": "Yes",
          "notes": "The impact test that puts a ticket at this level"
        }
      ],
      "relations": [
        {
          "property": "appliesTo",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "hasSeverity"
        }
      ],
      "individuals": "Closed set of four individuals. The definitions below are the organization's single severity standard and apply to every product (`OQ-19`).",
      "disjoint": "None.",
      "constraints": [
        "C-04 — every Ticket has exactly one SeverityLevel.",
        "C-25 — the set of levels is closed at four. A product-specific value that",
        "C-26 — comparisons and filters on severity must operate on levelRank,"
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "The per-ticket value in the product's own vocabulary",
          "authoritative": "Raw value only"
        },
        {
          "system": "This ontology",
          "supplies": "The canonical four levels and the alias map",
          "authoritative": "levelCode, levelRank"
        },
        {
          "system": "Organization-wide support policy",
          "supplies": "Impact definitions",
          "authoritative": "definition"
        }
      ],
      "questions": [
        "CQ-02",
        "CQ-08",
        "CQ-10",
        "CQ-15",
        "CQ-17",
        "CQ-23",
        "CQ-26",
        "CQ-27"
      ],
      "openQuestions": [
        "OQ-19",
        "OQ-51",
        "OQ-20",
        "OQ-44"
      ],
      "search": "severitylevel the graded measure of a ticket's business impact and urgency, used to set\nresponse expectations and routing. every ticket has exactly one.\n\n naming:  depending on the product, this is called  severity  or  priority .\nthese are the same attribute under two labels. see  eq-03 . the risk is\nparticularly sharp here because both words are also used loosely in conversation\nto mean \"how bad is it\" — an agent must resolve the term against the product\nbefore comparing values across products.   context   term used  \n --- --- \n  canonical   severitylevel  \n  products using severity naming   severity, sev  \n  products using priority naming    priority , pri  \n  escalation conversations   impact, urgency (informal, not a field)  \n\nwhich label a given product uses is recorded on  sup:product.severitytermused . closed set of four individuals.  the definitions below are the organization's\nsingle severity standard and apply to every product  ( oq-19 ).\n\n  canonical   rank   name   common aliases  \n --- --- --- --- \n   s1    1   system down   p1, critical, urgent, 1  \n   s2    2   work stoppage   p2, high, 2  \n   s3    3   medium   p3, medium, normal, 3  \n   s4    4   low   p4, low, minor, 4  \n\n   definition  — the impact test per level\n\nthese are  template definitions . replace them with your organization's own\nsupport policy wording when you adopt the ontology; the structure (four ranked\nlevels, one impact test each) is what the rest of the model depends on.\n\n s1 — system down.  a production environment is unavailable to all users, or\nno user can sign in. work has stopped. s1 handling assumes a customer contact is\navailable to troubleshoot; if nobody is, the ticket drops to s2.\n\n s2 — work stoppage.  part of the product is unusable, or some users cannot\ncomplete a critical task. others can keep working, but a fix or workaround is\nneeded. a full outage of a non-production environment is also s2.\n\n s3 — medium.  a problem that needs investigation or scheduled work but is\nnot stopping anyone. resolution time is agreed with the customer.\n\n s4 — low.  how-to questions, planned maintenance and upgrades, enhancement\nrequests and documentation issues. usually closed on first contact.\n\n  who sets it, and when it changes\nsupport sets the severity.  the customer has the right to request an escalation\nor de-escalation of a case , and the s1 rule above de-escalates automatically\nwhen the customer contact is unavailable.\n\nseverity is therefore  mutable over a ticket's life , by two named mechanisms.\nthe model currently stores only the current value — see  oq-20 , which this\ndefinition makes materially more important than it was.\n\n do not compare severity values as raw strings across products.  \"p1\" and\n\"s1\" are equal; \"priority 1\" and \"severity 1\" are equal. because the standard is\nnow uniform, any product whose data does not resolve cleanly to s1–s4 is a data\nconformance defect to be recorded, not a fifth level — see  oq-51 ."
    },
    {
      "id": "SupportAgent",
      "file": "Ontology/Entities/SupportAgent.md",
      "type": "Support",
      "status": "Canonical",
      "definition": "An internal member of the support organization who is assigned tickets, resolves them using documentation, and escalates to development when a ticket is caused by a defect or requires new functionality.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "SupportAgent"
        },
        {
          "context": "CRM",
          "term": "Case owner, Assigned to, Owner"
        },
        {
          "context": "Team language",
          "term": "Support engineer, Technical support, Analyst"
        },
        {
          "context": "Tiered teams",
          "term": "T1, T2, T3 agent"
        }
      ],
      "identity": "The CRM user ID is authoritative. Agents appearing in more than one CRM are matched on corporate email.",
      "attributes": [
        {
          "name": "agentId",
          "type": "string",
          "required": "Yes",
          "notes": "CRM user ID"
        },
        {
          "name": "tier",
          "type": "enum(T1, T2, T3)",
          "required": "No",
          "notes": "Support tier, where the team is tiered"
        },
        {
          "name": "isActive",
          "type": "boolean",
          "required": "Yes",
          "notes": "Currently holding the role"
        }
      ],
      "relations": [
        {
          "property": "handles",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "assignedTo"
        },
        {
          "property": "escalates",
          "target": "Escalation",
          "cardinality": "0..*",
          "inverse": "escalatedBy"
        },
        {
          "property": "consults",
          "target": "Documentation",
          "cardinality": "0..*",
          "inverse": "isConsultedBy"
        },
        {
          "property": "specialisesIn",
          "target": "Product",
          "cardinality": "0..*",
          "inverse": "isSupportedBy"
        },
        {
          "property": "measuredAgainst",
          "target": "SLA",
          "cardinality": "0..*",
          "inverse": "measures"
        }
      ],
      "individuals": "None. `tier` carries the seniority distinction.",
      "disjoint": "`sup:Contact` — an agent acts for us, a contact acts for the customer. Also disjoint with `sup:SalesRepresentative` and `sup:CustomerSuccessManager`: these are three distinct jobs. See `C-52`.",
      "constraints": [
        "C-29 — only a SupportAgent may create an Escalation.",
        "C-52 — SupportAgent, SalesRepresentative and CustomerSuccessManager are",
        "C-31 — a Ticket may be assigned to at most one SupportAgent at a time.",
        "C-32 — an inactive agent (isActive = false) must not hold open tickets."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "User record, case ownership",
          "authoritative": "agentId, handles"
        },
        {
          "system": "Support team structure",
          "supplies": "Tier and product specialisation",
          "authoritative": "tier, specialisesIn"
        }
      ],
      "questions": [
        "CQ-10",
        "CQ-12",
        "CQ-15",
        "CQ-16",
        "CQ-18",
        "CQ-30"
      ],
      "openQuestions": [
        "OQ-16",
        "OQ-23",
        "OQ-48"
      ],
      "search": "supportagent an internal member of the support organization who is assigned tickets, resolves\nthem using documentation, and escalates to development when a ticket is caused\nby a defect or requires new functionality.   context   term used  \n --- --- \n  canonical   supportagent  \n  crm   case owner, assigned to, owner  \n  team language   support engineer, technical support, analyst  \n  tiered teams   t1, t2, t3 agent   none.  tier  carries the seniority distinction."
    },
    {
      "id": "Ticket",
      "file": "Ontology/Entities/Ticket.md",
      "type": "Support",
      "status": "Canonical",
      "definition": "A single recorded request for support from a customer account, tracked from submission to resolution. One ticket represents one customer problem. It is owned by exactly one account, assigned to at most one agent at a time, carries exactly one severity, is governed by exactly one SLA, and may be escalated to development. It may be submitted by a Contact at the account or, where the customer buys through one, by a Partner acting on the account's behalf.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "Ticket"
        },
        {
          "context": "CRM systems using Case terminology",
          "term": "Case"
        },
        {
          "context": "ITSM-influenced teams",
          "term": "Incident"
        },
        {
          "context": "Older systems",
          "term": "SR, Service Request"
        }
      ],
      "identity": "The CRM ticket/case number is authoritative. Ticket numbers are unique within a CRM but not across CRMs — a fully qualified ticket identity is `systemCode` + `ticketNumber`. This is a real collision risk in reporting.",
      "attributes": [
        {
          "name": "ticketNumber",
          "type": "string",
          "required": "Yes",
          "notes": "CRM case number"
        },
        {
          "name": "subject",
          "type": "string",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "status",
          "type": "enum(New, Open, Pending, Escalated, Resolved, Closed)",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "openedAt",
          "type": "datetime",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "resolvedAt",
          "type": "datetime",
          "required": "No",
          "notes": "Required when status is Resolved or Closed"
        },
        {
          "name": "resolutionSummary",
          "type": "text",
          "required": "No",
          "notes": ""
        }
      ],
      "relations": [
        {
          "property": "belongsTo",
          "target": "Account",
          "cardinality": "1..1",
          "inverse": "raises"
        },
        {
          "property": "submittedBy",
          "target": "Contact",
          "cardinality": "0..1",
          "inverse": "submits"
        },
        {
          "property": "submittedByPartner",
          "target": "Partner",
          "cardinality": "0..1",
          "inverse": "raisesOnBehalfOf"
        },
        {
          "property": "assignedTo",
          "target": "SupportAgent",
          "cardinality": "0..1",
          "inverse": "handles"
        },
        {
          "property": "hasSeverity",
          "target": "SeverityLevel",
          "cardinality": "1..1",
          "inverse": "appliesTo"
        },
        {
          "property": "isGovernedBy",
          "target": "SLA",
          "cardinality": "1..1",
          "inverse": "governs"
        },
        {
          "property": "concerns",
          "target": "Product",
          "cardinality": "1..1",
          "inverse": "isSubjectOf"
        },
        {
          "property": "escalatedAs",
          "target": "Escalation",
          "cardinality": "0..*",
          "inverse": "originatesFrom"
        },
        {
          "property": "resolvedUsing",
          "target": "Documentation",
          "cardinality": "0..*",
          "inverse": "resolves"
        },
        {
          "property": "recordedIn",
          "target": "CRM",
          "cardinality": "1..1",
          "inverse": "records"
        }
      ],
      "individuals": "None. Ticket type distinctions (question vs defect vs request) are captured by the presence and type of an `Escalation`, not by subclassing the ticket.",
      "disjoint": "`sup:JiraIssue`. A ticket is a customer's request; a Jira issue is an internal work item. They are linked through an Escalation and are routinely confused — \"the ticket is fixed\" and \"the bug is fixed\" are different statements.",
      "constraints": [
        "C-04 — every Ticket has exactly one Account, one SeverityLevel and one",
        "C-05 — a Ticket may carry a Jira ID only through an Escalation. A ticket",
        "C-06 — a Ticket with status = Escalated must have at least one open",
        "C-16 — the submitting Contact must belong to the Ticket's Account.",
        "C-24 — resolvedAt is required when status is Resolved or Closed, and must",
        "C-56 — Every Ticket has exactly one SLA.",
        "C-57 — A Ticket raised by a Partner must belong to an Account that the Partner represents."
      ],
      "provenance": [
        {
          "system": "CRM",
          "supplies": "The ticket record and all its fields",
          "authoritative": "Everything except escalation links"
        },
        {
          "system": "Jira",
          "supplies": "Escalation linkage confirmation",
          "authoritative": "Nothing on the ticket directly"
        }
      ],
      "questions": [
        "CQ-01",
        "CQ-02",
        "CQ-03",
        "CQ-06",
        "CQ-08",
        "CQ-10",
        "CQ-11",
        "CQ-15",
        "CQ-17",
        "CQ-18",
        "CQ-23",
        "CQ-26",
        "CQ-27",
        "CQ-30",
        "CQ-31",
        "CQ-32"
      ],
      "openQuestions": [
        "OQ-16",
        "OQ-17",
        "OQ-18",
        "OQ-48",
        "OQ-49"
      ],
      "search": "ticket a single recorded request for support from a customer account, tracked from\nsubmission to resolution. one ticket represents one customer problem. it is\nowned by exactly one account, assigned to at most one agent at a time, carries\nexactly one severity, is governed by exactly one sla, and may be escalated to\ndevelopment. it may be submitted by a contact at the account or, where the\ncustomer buys through one, by a partner acting on the account's behalf.\n\n naming:  some crm systems call this a  case . ticket and case are the same\nclass — they are not related classes, not parent and child, and not similar\nthings. they are the same thing under two labels. see  eq-01 .   context   term used  \n --- --- \n  canonical   ticket  \n  crm systems using case terminology    case   \n  itsm-influenced teams   incident  \n  older systems   sr, service request  \n\nwhich label a given system uses is recorded on  sup:crm.tickettermused , not\nguessed. none. ticket type distinctions (question vs defect vs request) are captured by\nthe presence and type of an  escalation , not by subclassing the ticket."
    },
    {
      "id": "JiraIssue",
      "file": "Ontology/Entities/JiraIssue.md",
      "type": "Engineering",
      "status": "Canonical",
      "definition": "A unit of engineering work tracked in Jira, created as the result of a support escalation, representing either a defect to fix or a capability to build. Its key is the identifier that gets associated back to the originating ticket.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "JiraIssue"
        },
        {
          "context": "Everyday speech",
          "term": "Jira, Jira ID, ticket (dangerous — see below)"
        },
        {
          "context": "Development",
          "term": "Issue, Story, Bug, Defect"
        },
        {
          "context": "CRM field",
          "term": "Jira reference, Dev ID"
        }
      ],
      "identity": "The Jira issue key (e.g. `PROJ-1234`) is authoritative and globally unique.",
      "attributes": [
        {
          "name": "issueKey",
          "type": "string",
          "required": "Yes",
          "notes": "e.g. PROJ-1234"
        },
        {
          "name": "issueType",
          "type": "enum(Bug, Enhancement)",
          "required": "Yes",
          "notes": "Matches escalation type at creation"
        },
        {
          "name": "issueStatus",
          "type": "string",
          "required": "Yes",
          "notes": "Jira workflow status — varies by project"
        },
        {
          "name": "isResolved",
          "type": "boolean",
          "required": "Yes",
          "notes": "Normalised across the varying workflows"
        },
        {
          "name": "fixVersion",
          "type": "string",
          "required": "No",
          "notes": "Release that carries the fix"
        },
        {
          "name": "createdAt",
          "type": "datetime",
          "required": "Yes",
          "notes": ""
        }
      ],
      "relations": [
        {
          "property": "raisedBy",
          "target": "Escalation",
          "cardinality": "1..*",
          "inverse": "producedIssue"
        }
      ],
      "individuals": "None. `issueType` carries the Bug / Enhancement distinction, kept consistent with `sup:Escalation.escalationType`.",
      "disjoint": "`sup:Ticket`. This is the single most important disjointness declaration in the ontology, because natural language constantly merges them.",
      "constraints": [
        "C-27 — issue type matches the originating escalation's type at creation.",
        "C-33 — every JiraIssue traces back to at least one Escalation. A Jira issue",
        "C-34 — isResolved must be derived from a per-project mapping of Jira",
        "C-35 — a resolved JiraIssue with unresolved originating tickets is a"
      ],
      "provenance": [
        {
          "system": "Jira",
          "supplies": "The issue and all its fields",
          "authoritative": "Everything"
        },
        {
          "system": "Jira project configuration",
          "supplies": "Status-to-resolved mapping",
          "authoritative": "isResolved derivation"
        },
        {
          "system": "Salesforce",
          "supplies": "The Jira key stored on the case",
          "authoritative": "Nothing — mirror only"
        }
      ],
      "questions": [
        "CQ-11",
        "CQ-17",
        "CQ-18",
        "CQ-19"
      ],
      "openQuestions": [
        "OQ-24",
        "OQ-25",
        "OQ-15",
        "OQ-43"
      ],
      "search": "jiraissue a unit of engineering work tracked in jira, created as the result of a support\nescalation, representing either a defect to fix or a capability to build. its\nkey is the identifier that gets associated back to the originating ticket.   context   term used  \n --- --- \n  canonical   jiraissue  \n  everyday speech   jira, jira id, ticket ( dangerous — see below )  \n  development   issue, story, bug, defect  \n  crm field   jira reference, dev id  \n\n vocabulary hazard.  developers routinely call a jira issue a \"ticket\". support\nagents call a customer request a \"ticket\". in a mixed conversation — or in an\nagent's prompt context — \"the ticket is closed\" is genuinely ambiguous and the\ntwo are often in different states at the same time. always disambiguate.\nsee  eq-04 . none.  issuetype  carries the bug / enhancement distinction, kept consistent\nwith  sup:escalation.escalationtype ."
    },
    {
      "id": "Documentation",
      "file": "Ontology/Entities/Documentation.md",
      "type": "Knowledge",
      "status": "Canonical",
      "definition": "Published product documentation and knowledge base content that support agents consult to resolve tickets. One instance is one published unit — an article or page — identified by its URL.",
      "aliases": [
        {
          "context": "Canonical",
          "term": "Documentation"
        },
        {
          "context": "KB tooling",
          "term": "Article, KB article, Doc, Page"
        },
        {
          "context": "Agent conversation",
          "term": "The docs, the wiki"
        },
        {
          "context": "Content team",
          "term": "Content, Topic"
        }
      ],
      "identity": "The published URL is authoritative. Where content exists at several URLs (localised or mirrored), the canonical URL is the identity and the others are recorded as aliases.",
      "attributes": [
        {
          "name": "articleUrl",
          "type": "string",
          "required": "Yes",
          "notes": "Canonical published URL — the identity"
        },
        {
          "name": "title",
          "type": "string",
          "required": "Yes",
          "notes": ""
        },
        {
          "name": "lastReviewedAt",
          "type": "date",
          "required": "No",
          "notes": "Staleness signal for C-40"
        },
        {
          "name": "isPublic",
          "type": "boolean",
          "required": "Yes",
          "notes": "Whether customers can reach it"
        }
      ],
      "relations": [
        {
          "property": "describes",
          "target": "Product",
          "cardinality": "1..1",
          "inverse": "isDescribedBy"
        },
        {
          "property": "isConsultedBy",
          "target": "SupportAgent",
          "cardinality": "0..*",
          "inverse": "consults"
        },
        {
          "property": "resolves",
          "target": "Ticket",
          "cardinality": "0..*",
          "inverse": "resolvedUsing"
        }
      ],
      "individuals": "None enumerated. Loaded from the KB source inventories.",
      "disjoint": "None.",
      "constraints": [
        "C-23 — documentation describing an EndOfLife product is a retirement",
        "C-40 — an article with no lastReviewedAt in the last 24 months is a review",
        "C-55 — every Documentation instance describes exactly one Product. Content"
      ],
      "provenance": [
        {
          "system": "KB / documentation platform",
          "supplies": "The article and its content",
          "authoritative": "Everything"
        },
        {
          "system": "KB source inventories (sources.json per product)",
          "supplies": "Which articles are tracked",
          "authoritative": "Coverage set"
        },
        {
          "system": "CRM",
          "supplies": "Articles cited on resolved cases",
          "authoritative": "resolves"
        }
      ],
      "questions": [
        "CQ-12",
        "CQ-16",
        "CQ-24",
        "CQ-26"
      ],
      "openQuestions": [
        "OQ-29",
        "OQ-30",
        "OQ-45",
        "OQ-46"
      ],
      "search": "documentation published product documentation and knowledge base content that support agents\nconsult to resolve tickets. one instance is one published unit — an article or\npage — identified by its url.\n\ndocumentation is the support organization's shared memory. a wrong article does\nnot produce one wrong answer; it produces one wrong answer per agent who reads\nit.   context   term used  \n --- --- \n  canonical   documentation  \n  kb tooling   article, kb article, doc, page  \n  agent conversation   the docs, the wiki  \n  content team   content, topic   none enumerated. loaded from the kb source inventories."
    }
  ],
  "edges": [
    {
      "source": "Account",
      "target": "Region",
      "property": "isLocatedIn",
      "inverse": "isRegionOf",
      "cardinality": "1..1",
      "type": "Customer",
      "transitive": false,
      "note": "Drives sales rep assignment via C-46"
    },
    {
      "source": "Account",
      "target": "SupportEntitlement",
      "property": "hasEntitlement",
      "inverse": "entitles",
      "cardinality": "1..1",
      "type": "Customer",
      "transitive": false,
      "note": "Premium ≡ Platinum — resolve before comparing"
    },
    {
      "source": "Account",
      "target": "License",
      "property": "holdsLicense",
      "inverse": "isHeldBy",
      "cardinality": "0..*",
      "type": "Customer",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Account",
      "target": "Ticket",
      "property": "raises",
      "inverse": "belongsTo",
      "cardinality": "0..*",
      "type": "Customer",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Account",
      "target": "SalesRepresentative",
      "property": "hasSalesRep",
      "inverse": "manages",
      "cardinality": "1..1",
      "type": "Customer",
      "transitive": false,
      "note": "Rep must cover the account's region — C-46"
    },
    {
      "source": "Account",
      "target": "CustomerSuccessManager",
      "property": "hasCSM",
      "inverse": "supports",
      "cardinality": "0..1",
      "type": "Customer",
      "transitive": false,
      "note": "Conditional — only if isStrategic — C-08"
    },
    {
      "source": "Account",
      "target": "Contact",
      "property": "hasContact",
      "inverse": "worksFor",
      "cardinality": "0..*",
      "type": "Customer",
      "transitive": false,
      "note": "Contact is Proposed"
    },
    {
      "source": "Account",
      "target": "Partner",
      "property": "isRepresentedBy",
      "inverse": "represents",
      "cardinality": "0..*",
      "type": "Customer",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Contact",
      "target": "Ticket",
      "property": "submits",
      "inverse": "submittedBy",
      "cardinality": "0..*",
      "type": "Customer",
      "transitive": false,
      "note": "Contact must belong to the ticket's account — C-16"
    },
    {
      "source": "CRM",
      "target": "Ticket",
      "property": "records",
      "inverse": "recordedIn",
      "cardinality": "0..*",
      "type": "Support",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Documentation",
      "target": "Product",
      "property": "describes",
      "inverse": "isDescribedBy",
      "cardinality": "1..1",
      "type": "Knowledge",
      "transitive": false,
      "note": "Soft cardinality — C-55"
    },
    {
      "source": "Documentation",
      "target": "SupportAgent",
      "property": "isConsultedBy",
      "inverse": "consults",
      "cardinality": "0..*",
      "type": "Knowledge",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Documentation",
      "target": "Ticket",
      "property": "resolves",
      "inverse": "resolvedUsing",
      "cardinality": "0..*",
      "type": "Knowledge",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Escalation",
      "target": "Ticket",
      "property": "originatesFrom",
      "inverse": "escalatedAs",
      "cardinality": "1..1",
      "type": "Support",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Escalation",
      "target": "JiraIssue",
      "property": "producedIssue",
      "inverse": "raisedBy",
      "cardinality": "1..1",
      "type": "Support",
      "transitive": false,
      "note": "Inverse is 1..* — many escalations, one issue"
    },
    {
      "source": "Escalation",
      "target": "SupportAgent",
      "property": "escalatedBy",
      "inverse": "escalates",
      "cardinality": "1..1",
      "type": "Support",
      "transitive": false,
      "note": "Only agents may escalate — C-29"
    },
    {
      "source": "License",
      "target": "Product",
      "property": "grantsAccessTo",
      "inverse": "isLicensedBy",
      "cardinality": "1..1",
      "type": "Customer",
      "transitive": false,
      "note": ""
    },
    {
      "source": "License",
      "target": "SupportEntitlement",
      "property": "isBoundTo",
      "inverse": "binds",
      "cardinality": "1..1",
      "type": "Customer",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Partner",
      "target": "Ticket",
      "property": "raisesOnBehalfOf",
      "inverse": "submittedByPartner",
      "cardinality": "0..*",
      "type": "Customer",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Product",
      "target": "Ticket",
      "property": "isSubjectOf",
      "inverse": "concerns",
      "cardinality": "0..*",
      "type": "Product",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Product",
      "target": "SupportAgent",
      "property": "isSupportedBy",
      "inverse": "specialisesIn",
      "cardinality": "0..*",
      "type": "Product",
      "transitive": false,
      "note": ""
    },
    {
      "source": "Region",
      "target": "SalesRepresentative",
      "property": "isCoveredBy",
      "inverse": "covers",
      "cardinality": "1..*",
      "type": "Customer",
      "transitive": false,
      "note": ""
    },
    {
      "source": "SeverityLevel",
      "target": "Ticket",
      "property": "appliesTo",
      "inverse": "hasSeverity",
      "cardinality": "0..*",
      "type": "Support",
      "transitive": false,
      "note": ""
    },
    {
      "source": "SLA",
      "target": "Ticket",
      "property": "governs",
      "inverse": "isGovernedBy",
      "cardinality": "0..*",
      "type": "Support",
      "transitive": false,
      "note": ""
    },
    {
      "source": "SLA",
      "target": "SupportAgent",
      "property": "measures",
      "inverse": "measuredAgainst",
      "cardinality": "0..*",
      "type": "Support",
      "transitive": false,
      "note": ""
    },
    {
      "source": "SupportAgent",
      "target": "Ticket",
      "property": "handles",
      "inverse": "assignedTo",
      "cardinality": "0..*",
      "type": "Support",
      "transitive": false,
      "note": ""
    }
  ]
};
