import { mandatoryCaveats } from "@/lib/caveats";

type CaveatBannerProps = {
  compact?: boolean;
};

export function CaveatBanner({ compact = false }: CaveatBannerProps) {
  const caveats = compact ? mandatoryCaveats.slice(0, 3) : mandatoryCaveats;
  return (
    <section className="caveats" aria-label="Mandatory caveats">
      <strong>Mandatory research caveats</strong>
      <ul>
        {caveats.map((caveat) => (
          <li key={caveat}>{caveat}</li>
        ))}
      </ul>
    </section>
  );
}
