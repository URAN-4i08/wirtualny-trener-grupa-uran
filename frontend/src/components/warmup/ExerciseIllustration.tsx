type ExerciseIllustrationProps = {
  name: string;
};

export default function ExerciseIllustration({ name }: ExerciseIllustrationProps) {
  const key = name.toLowerCase();

  if (key.includes('ramion')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        <circle cx="100" cy="35" r="14" fill="none" stroke="#ffb690" strokeWidth="2" />
        <line x1="100" y1="49" x2="100" y2="95" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="100" y1="60" x2="55" y2="45" stroke="#ffb690" strokeWidth="3" strokeLinecap="round" />
        <line x1="100" y1="60" x2="145" y2="45" stroke="#ffb690" strokeWidth="3" strokeLinecap="round" />
        <path d="M55 45 Q35 25 55 15" fill="none" stroke="#f97316" strokeWidth="2" strokeDasharray="4 3" />
        <path d="M145 45 Q165 25 145 15" fill="none" stroke="#f97316" strokeWidth="2" strokeDasharray="4 3" />
        <line x1="100" y1="95" x2="80" y2="140" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="100" y1="95" x2="120" y2="140" stroke="#7bd0ff" strokeWidth="3" />
      </svg>
    );
  }

  if (key.includes('przysiad')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        <circle cx="100" cy="50" r="14" fill="none" stroke="#ffb690" strokeWidth="2" />
        <line x1="100" y1="64" x2="100" y2="95" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="100" y1="75" x2="70" y2="85" stroke="#ffb690" strokeWidth="3" />
        <line x1="100" y1="75" x2="130" y2="85" stroke="#ffb690" strokeWidth="3" />
        <line x1="85" y1="95" x2="65" y2="115" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="85" y1="115" x2="55" y2="125" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="115" y1="95" x2="135" y2="115" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="115" y1="115" x2="145" y2="125" stroke="#7bd0ff" strokeWidth="3" />
      </svg>
    );
  }

  if (key.includes('wykrok')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        <circle cx="95" cy="40" r="14" fill="none" stroke="#ffb690" strokeWidth="2" />
        <line x1="95" y1="54" x2="95" y2="90" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="80" y1="90" x2="60" y2="135" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="110" y1="90" x2="150" y2="120" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="150" y1="120" x2="165" y2="140" stroke="#f97316" strokeWidth="3" />
      </svg>
    );
  }

  if (key.includes('plank')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        <circle cx="40" cy="80" r="12" fill="none" stroke="#ffb690" strokeWidth="2" />
        <line x1="52" y1="82" x2="150" y2="82" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="150" y1="82" x2="170" y2="105" stroke="#7bd0ff" strokeWidth="3" />
        <line x1="60" y1="82" x2="55" y2="110" stroke="#f97316" strokeWidth="2" />
        <line x1="130" y1="82" x2="135" y2="110" stroke="#f97316" strokeWidth="2" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
      <circle cx="100" cy="30" r="20" fill="none" stroke="#f97316" strokeWidth="2" />
      <path d="M100 50 L100 70" stroke="#7bd0ff" strokeWidth="2" />
      <path d="M70 55 L130 55" stroke="#ffb690" strokeWidth="3" strokeLinecap="round" />
      <circle cx="100" cy="30" r="8" fill="#f97316" opacity="0.3" />
      <text x="100" y="120" textAnchor="middle" fill="#e0c0b1" fontSize="12" fontFamily="Inter">
        odbicie
      </text>
    </svg>
  );
}
