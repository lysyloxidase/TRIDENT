"use client";

import Script from "next/script";

export function MoleculeViewer({ gene }: { gene: string }) {
  return (
    <div className="viewer">
      <Script src="https://3dmol.org/build/3Dmol-min.js" strategy="afterInteractive" />
      <div className="protein-scene" aria-label={`${gene} pocket structure`}>
        <div className="helix h1" />
        <div className="helix h2" />
        <div className="helix h3" />
        <div className="pocket-highlight" />
        <div className="ligand-stick l1" />
        <div className="ligand-stick l2" />
        <span className="viewer-label">{gene} pocket</span>
      </div>
    </div>
  );
}
