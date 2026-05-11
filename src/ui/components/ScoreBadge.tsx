type ScoreBadgeProps = {
  tdl: "Tdark" | "Tbio" | "Tchem" | "Tclin";
};

export function ScoreBadge({ tdl }: ScoreBadgeProps) {
  return <span className={`badge ${tdl.toLowerCase()}`}>{tdl}</span>;
}
