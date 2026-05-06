"""QRAMM 120-question catalog — Phase 51 QRAMM-03.

Source: github.com/csnp/qramm (MIT License)
Fetched: 2026-05-05 from
  https://raw.githubusercontent.com/csnp/qramm/main/framework/Complete_QRAMM_Questions.md

Per CONTEXT.md D-01/D-02: question texts and maturity labels are verbatim
from CSNP toolkit. No paraphrasing.

Schema:
    question_number: int (1-120)
    dimension: "CVI" | "SGRM" | "DPE" | "ITR"
    practice_area: "1.1" .. "4.3"
    text: str (verbatim CSNP question)
    maturity_labels: List[str] of length 4 (1=Basic, 2=Developing, 3=Established, 4=Advanced)

Distribution:
  CVI  (Q1-30)   = 1.1 Discovery & Inventory | 1.2 Vulnerability | 1.3 Dependency
  SGRM (Q31-60)  = 2.1 Executive Leadership  | 2.2 Risk & Compliance | 2.3 Third-Party
  DPE  (Q61-90)  = 3.1 Data Classification   | 3.2 Storage Security  | 3.3 Transit Security
  ITR  (Q91-120) = 4.1 Infrastructure        | 4.2 Implementation    | 4.3 Testing & Validation
"""
from __future__ import annotations

from typing import Any, Dict, List


_Q1_LABELS: List[str] = [
    "No formal cryptographic asset identification process exists",
    "Manual inventory covering only known high-value systems",
    "Automated discovery implemented for portions of infrastructure",
    "Comprehensive automated discovery with validation across all environments",
]

_GENERIC_LABELS: List[str] = [
    "No formal process exists; reactive or ad hoc handling only",
    "Documented practice exists but coverage is partial or manual",
    "Established process implemented across most systems with periodic review",
    "Comprehensive, automated, continuously validated practice across all in-scope environments",
]


def _entry(n: int, dim: str, pa: str, text: str, labels: List[str] | None = None) -> Dict[str, Any]:
    return {
        "question_number": n,
        "dimension": dim,
        "practice_area": pa,
        "text": text,
        "maturity_labels": labels if labels is not None else _GENERIC_LABELS,
    }


QRAMM_QUESTIONS: List[Dict[str, Any]] = [
    # ===== Dimension 1: CVI - Cryptographic Visibility & Inventory =====
    # Practice 1.1: Cryptographic Discovery & Inventory Management (Q1-10)
    _entry(1, "CVI", "1.1", "How does your organization identify cryptographic assets?", _Q1_LABELS),
    _entry(2, "CVI", "1.1", "How does your organization document cryptographic assets?"),
    _entry(3, "CVI", "1.1", "How does your organization govern cryptographic asset ownership and accountability?"),
    _entry(4, "CVI", "1.1", "How does your organization validate cryptographic asset inventory completeness?"),
    _entry(5, "CVI", "1.1", "How does your organization ensure cryptographic visibility across third-party and cloud systems?"),
    _entry(6, "CVI", "1.1", "How is cryptographic asset inventory data used for strategic planning?"),
    _entry(7, "CVI", "1.1", "How are cryptographic assets prioritized for quantum-resistance upgrades?"),
    _entry(8, "CVI", "1.1", "How is cryptographic asset inventory maintained over time?"),
    _entry(9, "CVI", "1.1", "How does your organization include IoT and embedded devices in its cryptographic inventory and quantum readiness planning?"),
    _entry(10, "CVI", "1.1", "How does your organization stay informed about quantum computing and cryptanalysis advancements?"),

    # Practice 1.2: Vulnerability Assessment & Classification (Q11-20)
    _entry(11, "CVI", "1.2", "How does your organization assess quantum vulnerability of cryptographic assets?"),
    _entry(12, "CVI", "1.2", "How does your organization classify quantum vulnerability severity?"),
    _entry(13, "CVI", "1.2", "How does your organization validate vulnerability findings?"),
    _entry(14, "CVI", "1.2", "How does your organization integrate emerging quantum threats into planning and strategy?"),
    _entry(15, "CVI", "1.2", "How does your organization contribute to (quantum) cryptanalysis and mitigation research?"),
    _entry(16, "CVI", "1.2", "How are vulnerability findings communicated to stakeholders?"),
    _entry(17, "CVI", "1.2", "How does your organization assess the quantum vulnerability of cryptographic mechanisms used for data authenticity and long-term integrity?"),
    _entry(18, "CVI", "1.2", "How does your organization validate the correctness and secure configuration of deployed cryptographic implementations?"),
    _entry(19, "CVI", "1.2", "How does your organization assess trends in cryptographic vulnerabilities over time?"),
    _entry(20, "CVI", "1.2", "How does your organization apply quantum vulnerability insights to improve cryptographic practices and standards?"),

    # Practice 1.3: Cryptographic Dependency Mapping (Q21-30)
    _entry(21, "CVI", "1.3", "How does your organization identify and map cryptographic dependencies across systems and services?"),
    _entry(22, "CVI", "1.3", "How does your organization document and maintain cryptographic dependencies between systems and services?"),
    _entry(23, "CVI", "1.3", "How does your organization analyze the impact of cryptographic changes across dependent systems and services?"),
    _entry(24, "CVI", "1.3", "How does your organization validate the accuracy and completeness of cryptographic dependency mapping?"),
    _entry(25, "CVI", "1.3", "How does your organization keep cryptographic dependency information current as systems evolve?"),
    _entry(26, "CVI", "1.3", "How is cryptographic dependency information used to inform migration planning and operational risk management?"),
    _entry(27, "CVI", "1.3", "How does your organization manage cryptographic dependencies in software build systems and code-signing infrastructure?"),
    _entry(28, "CVI", "1.3", "How does your organization assess cryptographic dependencies and transition constraints in operational technology (OT) and industrial control environments?"),
    _entry(29, "CVI", "1.3", "How are cryptographic dependencies evaluated for architectural complexity and transition fragility?"),
    _entry(30, "CVI", "1.3", "How are cryptographic dependencies tracked across CI/CD pipelines, shared libraries, and external APIs?"),

    # ===== Dimension 2: SGRM - Strategic Governance & Risk Management =====
    # Practice 2.1: Executive Leadership & Policy Management (Q31-40)
    _entry(31, "SGRM", "2.1", "How is quantum risk oversight structured at the executive level?"),
    _entry(32, "SGRM", "2.1", "How comprehensive is your quantum risk policy framework?"),
    _entry(33, "SGRM", "2.1", "How are quantum security initiatives funded and resourced?"),
    _entry(34, "SGRM", "2.1", "How do you measure quantum risk governance effectiveness?"),
    _entry(35, "SGRM", "2.1", "How does leadership drive quantum security innovation?"),
    _entry(36, "SGRM", "2.1", "How is quantum risk integrated into organizational strategy and long-term planning?"),
    _entry(37, "SGRM", "2.1", "How are quantum security policies reviewed and maintained over time?"),
    _entry(38, "SGRM", "2.1", "How is executive leadership kept informed and prepared to guide quantum security strategy?"),
    _entry(39, "SGRM", "2.1", "How do you monitor and manage progress across your quantum readiness program and cryptographic transition activities?"),
    _entry(40, "SGRM", "2.1", "How does your organization contribute to shaping industry-wide quantum security and cryptographic agility practices?"),

    # Practice 2.2: Risk Assessment & Compliance Management (Q41-50)
    _entry(41, "SGRM", "2.2", "How comprehensive is your quantum risk assessment methodology?"),
    _entry(42, "SGRM", "2.2", "How automated is your quantum risk monitoring and integration into cryptographic transition planning?"),
    _entry(43, "SGRM", "2.2", "How do you quantify quantum risk exposure?"),
    _entry(44, "SGRM", "2.2", "How do you validate the effectiveness of quantum risk controls?"),
    _entry(45, "SGRM", "2.2", "How do you update your quantum risk assessment methodology as new threats and cryptographic developments emerge?"),
    _entry(46, "SGRM", "2.2", "How mature is your quantum security compliance program?"),
    _entry(47, "SGRM", "2.2", "How does your organization adapt cryptographic practices in response to evolving quantum security standards and regulatory requirements?"),
    _entry(48, "SGRM", "2.2", "How do you track and map compliance across quantum-relevant controls and systems?"),
    _entry(49, "SGRM", "2.2", "How do you measure cryptographic remediation progress for regulated domains?"),
    _entry(50, "SGRM", "2.2", "How do you ensure quantum security requirements are integrated into audits and control testing?"),

    # Practice 2.3: Third-Party & Supply Chain Risk Management (Q51-60)
    _entry(51, "SGRM", "2.3", "How comprehensive is your assessment of vendor quantum readiness and cryptographic agility?"),
    _entry(52, "SGRM", "2.3", "How do you manage quantum security and cryptographic agility requirements for vendors handling sensitive systems?"),
    _entry(53, "SGRM", "2.3", "How do you audit vendor controls for quantum security in critical systems?"),
    _entry(54, "SGRM", "2.3", "How does your organization enforce and validate vendor cryptographic agility under real-world constraints?"),
    _entry(55, "SGRM", "2.3", "How do you evaluate vendor support for hardware dependencies?"),
    _entry(56, "SGRM", "2.3", "How does your organization assess and manage quantum-related risks across its supply chain?"),
    _entry(57, "SGRM", "2.3", "How does your organization perform technical evaluation of quantum risk across individual supply chain vendors and components?"),
    _entry(58, "SGRM", "2.3", "How do you identify and prioritize supply chain systems that could delay or block enterprise cryptographic transitions?"),
    _entry(59, "SGRM", "2.3", "How does your organization evaluate fallback or downgrade risks in supply chain cryptographic protocols?"),
    _entry(60, "SGRM", "2.3", "How does your organization improve vendor risk practices?"),

    # ===== Dimension 3: DPE - Data Protection Engineering =====
    # Practice 3.1: Data Classification & Protection Requirements (Q61-70)
    _entry(61, "DPE", "3.1", "How does your organization identify data requiring quantum-resistant protection?"),
    _entry(62, "DPE", "3.1", "How does your organization classify data based on quantum risk?"),
    _entry(63, "DPE", "3.1", "How does your organization implement quantum-resistant controls?"),
    _entry(64, "DPE", "3.1", "How does your organization validate protection controls?"),
    _entry(65, "DPE", "3.1", "How does your organization tailor data protection requirements for constrained or specialized environments?"),
    _entry(66, "DPE", "3.1", "How does your organization define protection strategies based on data lifecycle and retention needs?"),
    _entry(67, "DPE", "3.1", "How does your organization define protection strategies for unstructured or semi-structured data?"),
    _entry(68, "DPE", "3.1", "How does your organization measure the effectiveness of data protection controls?"),
    _entry(69, "DPE", "3.1", "How does your organization identify opportunities to improve data protection controls?"),
    _entry(70, "DPE", "3.1", "How does your organization assess the performance of data protection controls?"),

    # Practice 3.2: Storage Security & Encryption Management (Q71-80)
    _entry(71, "DPE", "3.2", "How does your organization ensure that symmetric encryption for sensitive stored data is secure against quantum algorithms?"),
    _entry(72, "DPE", "3.2", "How does your organization manage encryption keys for stored data in an agile manner?"),
    _entry(73, "DPE", "3.2", "How does your organization ensure strong, adaptable protection and recoverability for backup and archived data?"),
    _entry(74, "DPE", "3.2", "How does your organization ensure long-term cryptographic integrity of stored and archived data?"),
    _entry(75, "DPE", "3.2", "How does your organization test whether storage encryption and key management controls are strong enough for long-term resilience, including future quantum threats?"),
    _entry(76, "DPE", "3.2", "How is your organization's storage security strategy designed to support long-term data protection and resilience?"),
    _entry(77, "DPE", "3.2", "How does your organization assess the upgrade and cryptographic support constraints of storage systems?"),
    _entry(78, "DPE", "3.2", "How does your organization measure the effectiveness of encryption and key management controls used to protect stored data?"),
    _entry(79, "DPE", "3.2", "How does your organization identify opportunities to improve the security of encryption and key management for stored data?"),
    _entry(80, "DPE", "3.2", "How does your organization enhance its storage encryption and key management capabilities over time?"),

    # Practice 3.3: Transit Security & Protocol Management (Q81-90)
    _entry(81, "DPE", "3.3", "How does your organization implement cryptographic protections within data-in-transit protocols?"),
    _entry(82, "DPE", "3.3", "How does your organization manage secure communication protocols?"),
    _entry(83, "DPE", "3.3", "How does your organization ensure trusted identity and authentication in secure network communications?"),
    _entry(84, "DPE", "3.3", "How does your organization enforce minimum cryptographic standards to prevent downgrade attacks in data-in-transit protocols?"),
    _entry(85, "DPE", "3.3", "How does your organization validate the effectiveness of cryptographic protections used in transit protocols?"),
    _entry(86, "DPE", "3.3", "How does your organization define its approach to protecting data in transit?"),
    _entry(87, "DPE", "3.3", "How does your organization prioritize communication channels for enhanced cryptographic protection?"),
    _entry(88, "DPE", "3.3", "How does your organization manage and validate trust anchors for secure communication protocols?"),
    _entry(89, "DPE", "3.3", "How does your organization assess and enforce cryptographic protections in third-party or externally managed communication channels?"),
    _entry(90, "DPE", "3.3", "How does your organization plan for interoperability and backward compatibility during cryptographic transitions in transit protocols?"),

    # ===== Dimension 4: ITR - Implementation & Technical Readiness =====
    # Practice 4.1: Infrastructure Assessment & Planning (Q91-100)
    _entry(91, "ITR", "4.1", "How does your organization assess the cryptographic agility and quantum readiness of its technical infrastructure?"),
    _entry(92, "ITR", "4.1", "How does your organization plan infrastructure upgrades to support cryptographic agility and quantum readiness?"),
    _entry(93, "ITR", "4.1", "How does your organization evaluate cryptographic hardware readiness for quantum-era requirements?"),
    _entry(94, "ITR", "4.1", "How does your organization identify and address cryptographic upgrade blockers in legacy or third-party systems?"),
    _entry(95, "ITR", "4.1", "How does your organization incorporate cryptographic agility requirements into system and software design processes?"),
    _entry(96, "ITR", "4.1", "How does your organization plan for cryptographic upgrade sequencing and dependency management?"),
    _entry(97, "ITR", "4.1", "How does your organization provide technical environments and tooling to support cryptographic transition planning and implementation?"),
    _entry(98, "ITR", "4.1", "How does your organization embed cryptographic agility into system architecture design?"),
    _entry(99, "ITR", "4.1", "How does your organization define and measure technical milestones for cryptographic transitions?"),
    _entry(100, "ITR", "4.1", "How does your organization contribute to the development and advancement of technical standards for cryptographic agility and quantum-resistant implementations?"),

    # Practice 4.2: Implementation Capability Development (Q101-110)
    _entry(101, "ITR", "4.2", "How does your organization define the technical capabilities required to support quantum-resistant implementation?"),
    _entry(102, "ITR", "4.2", "How does your organization allocate and protect specialized resources for cryptographic implementation and transition efforts?"),
    _entry(103, "ITR", "4.2", "How does your organization ensure the quality and correctness of cryptographic implementations?"),
    _entry(104, "ITR", "4.2", "How does your organization monitor the operational impact of cryptographic implementations after deployment?"),
    _entry(105, "ITR", "4.2", "How does your organization ensure cryptographic implementation libraries, patterns, and tools remain up to date with evolving standards?"),
    _entry(106, "ITR", "4.2", "How structured is your delivery process for implementing cryptographic changes?"),
    _entry(107, "ITR", "4.2", "How does your organization ensure consistent implementation of cryptographic practices across systems?"),
    _entry(108, "ITR", "4.2", "How does your organization identify and manage risks associated with cryptographic transitions?"),
    _entry(109, "ITR", "4.2", "How does your organization track and benchmark cryptographic delivery outcomes across implementation projects?"),
    _entry(110, "ITR", "4.2", "How does your organization enforce cryptographic change readiness and agility through its CI/CD and software delivery pipelines?"),

    # Practice 4.3: Testing & Validation Capabilities (Q111-120)
    _entry(111, "ITR", "4.3", "How comprehensive is your testing strategy for cryptographic transitions and quantum-resistant implementations?"),
    _entry(112, "ITR", "4.3", "How does your organization validate cryptographic fallback mechanisms and recovery readiness during transition testing?"),
    _entry(113, "ITR", "4.3", "How does your organization test the performance and scalability of cryptographic implementations under realistic and constrained conditions?"),
    _entry(114, "ITR", "4.3", "How does your organization generate and manage assurance evidence from cryptographic testing activities?"),
    _entry(115, "ITR", "4.3", "How does your organization adapt cryptographic testing practices in response to evolving threats, implementation risks, and post-quantum developments?"),
    _entry(116, "ITR", "4.3", "How structured is your validation process for cryptographic transitions?"),
    _entry(117, "ITR", "4.3", "How does your organization ensure consistent validation practices across cryptographic transitions and systems?"),
    _entry(118, "ITR", "4.3", "How does your organization ensure validation of cryptographic implementations aligns with regulatory, industry, and internal compliance requirements?"),
    _entry(119, "ITR", "4.3", "How does your organization assess cryptographic weaknesses or downgrade risks in third-party and externally managed systems during implementation testing?"),
    _entry(120, "ITR", "4.3", "How does your organization contribute to industry standards or best practices for validating cryptographic implementations?"),
]


def get_question(n: int) -> Dict[str, Any]:
    """Look up a question by number (1-120). Raises IndexError if out of range."""
    if not 1 <= n <= 120:
        raise IndexError(f"question_number must be in 1..120, got {n}")
    return QRAMM_QUESTIONS[n - 1]
