export type Target = {
  rank: number;
  gene: string;
  uniprot: string;
  tdl: "Tdark" | "Tbio" | "Tchem" | "Tclin";
  novelty: number;
  confidence: number;
  trident: number;
  evidence: string[];
};

export const recentRuns = [
  { id: "demo", disease: "Idiopathic pulmonary fibrosis", status: "complete", targets: 5 },
  { id: "dry-amd", disease: "Dry age-related macular degeneration", status: "complete", targets: 5 },
  { id: "nsclc", disease: "EGFR-mutated NSCLC", status: "complete", targets: 4 }
];

export const targets: Target[] = [
  {
    rank: 1,
    gene: "AKAP13",
    uniprot: "Q12802",
    tdl: "Tdark",
    novelty: 0.985,
    confidence: 0.991,
    trident: 0.976,
    evidence: ["MR posterior 0.58", "LBD 2-path support", "patent white-space 0.94"]
  },
  {
    rank: 2,
    gene: "PARN",
    uniprot: "O95453",
    tdl: "Tdark",
    novelty: 0.946,
    confidence: 0.988,
    trident: 0.935,
    evidence: ["GWAS PIP 0.74", "trial gap 0.82", "low contradiction burden"]
  },
  {
    rank: 3,
    gene: "MUC5B",
    uniprot: "Q9HC84",
    tdl: "Tbio",
    novelty: 0.769,
    confidence: 0.990,
    trident: 0.761,
    evidence: ["GWAS PIP 0.96", "expression specificity 0.84", "MR posterior 0.74"]
  },
  {
    rank: 4,
    gene: "DPP9",
    uniprot: "Q86TI2",
    tdl: "Tbio",
    novelty: 0.724,
    confidence: 0.985,
    trident: 0.713,
    evidence: ["enzyme pocket", "GWAS PIP 0.85", "patent white-space 0.71"]
  },
  {
    rank: 5,
    gene: "TERT",
    uniprot: "O14746",
    tdl: "Tbio",
    novelty: 0.501,
    confidence: 0.984,
    trident: 0.493,
    evidence: ["telomere biology", "MR posterior 0.69", "moderate patent crowding"]
  }
];

export const molecules = [
  {
    smiles: "C(=O)NN1CCN(CC1)C(=O)c2ccc(C(=O)N)cc2",
    affinity: -8.17,
    admet: 0.82,
    synthesis: 0.76
  },
  {
    smiles: "CCN1CCN(CC1)C(=O)c2ccc(OC)cc2",
    affinity: -7.92,
    admet: 0.79,
    synthesis: 0.81
  },
  {
    smiles: "COc1ccc(NC(=O)CCN)cc1",
    affinity: -7.44,
    admet: 0.74,
    synthesis: 0.86
  }
];

export const perturbationGenes = [
  { gene: "KRAS", log2fc: -0.8509, neglog10p: 6.2, variance: 0.0149 },
  { gene: "MAPK1", log2fc: -0.4324, neglog10p: 4.8, variance: 0.0101 },
  { gene: "MYC", log2fc: -0.5894, neglog10p: 5.7, variance: 0.0182 },
  { gene: "DUSP6", log2fc: 0.7203, neglog10p: 5.1, variance: 0.0127 },
  { gene: "ETV4", log2fc: -0.612, neglog10p: 3.9, variance: 0.0725 },
  { gene: "ETV5", log2fc: -0.566, neglog10p: 3.8, variance: 0.0639 }
];
