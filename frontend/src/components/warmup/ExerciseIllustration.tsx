type ExerciseIllustrationProps = {
  name: string;
};

export default function ExerciseIllustration({ name }: ExerciseIllustrationProps) {
  const key = name.toLowerCase();

  if (key.includes('ramion')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        <circle cx="100" cy="40" r="14" fill="none" stroke="#e2e8f0" strokeWidth="3" />
        <line x1="100" y1="54" x2="100" y2="100" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Legs */}
        <line x1="100" y1="100" x2="80" y2="145" stroke="#7bd0ff" strokeWidth="3" strokeLinecap="round" />
        <line x1="100" y1="100" x2="120" y2="145" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Arms */}
        <line x1="60" y1="70" x2="140" y2="70" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Dashed Circles */}
        <ellipse cx="50" cy="70" rx="12" ry="28" fill="none" stroke="#f97316" strokeWidth="2.5" strokeDasharray="6 4" />
        <ellipse cx="150" cy="70" rx="12" ry="28" fill="none" stroke="#f97316" strokeWidth="2.5" strokeDasharray="6 4" />
      </svg>
    );
  }

  if (key.includes('przysiad')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        {/* Glow on back */}
        <rect x="85" y="70" width="20" height="30" fill="#f97316" opacity="0.25" rx="4" transform="rotate(30 95 85)" />
        <circle cx="110" cy="40" r="12" fill="none" stroke="#e2e8f0" strokeWidth="3" />
        {/* Torso leaning forward */}
        <line x1="110" y1="52" x2="90" y2="90" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Arms straight forward */}
        <line x1="100" y1="65" x2="145" y2="75" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Legs: Thighs */}
        <line x1="90" y1="90" x2="120" y2="100" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        <line x1="90" y1="90" x2="130" y2="115" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Legs: Calves */}
        <line x1="120" y1="100" x2="110" y2="135" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        <line x1="130" y1="115" x2="125" y2="145" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Feet */}
        <line x1="110" y1="135" x2="125" y2="135" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        <line x1="125" y1="145" x2="140" y2="145" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Ground line */}
        <line x1="70" y1="150" x2="150" y2="150" stroke="#52525b" strokeWidth="2" />
        {/* Orange arrows down */}
        <path d="M75 80 L75 105 L70 100 M75 105 L80 100" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M140 95 L140 120 L135 115 M140 120 L145 115" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (key.includes('wykrok')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        <circle cx="130" cy="40" r="12" fill="none" stroke="#e2e8f0" strokeWidth="3" />
        <line x1="130" y1="52" x2="130" y2="95" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        <path d="M130 65 L115 80 L130 95" fill="none" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {/* Back leg */}
        <line x1="130" y1="95" x2="90" y2="115" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        <line x1="90" y1="115" x2="90" y2="145" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        <line x1="90" y1="145" x2="75" y2="145" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Front leg (orange highlight) */}
        <line x1="130" y1="95" x2="160" y2="95" stroke="#f97316" strokeWidth="3" strokeLinecap="round" />
        <line x1="160" y1="95" x2="160" y2="145" stroke="#f97316" strokeWidth="3" strokeLinecap="round" />
        <line x1="160" y1="145" x2="175" y2="145" stroke="#f97316" strokeWidth="3" strokeLinecap="round" />
        <line x1="70" y1="150" x2="180" y2="150" stroke="#52525b" strokeWidth="2" />
        <path d="M155 70 L170 70 L165 65 M170 70 L165 75" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (key.includes('odbicia')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        <circle cx="100" cy="40" r="12" fill="none" stroke="#e2e8f0" strokeWidth="3" />
        <line x1="100" y1="52" x2="95" y2="100" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        {/* Arms */}
        <path d="M98 65 L80 85 L90 105" fill="none" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M98 65 L115 85 L125 105" fill="none" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {/* Legs */}
        <path d="M95 100 L85 120 L80 140" fill="none" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M95 100 L115 115 L120 135" fill="none" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {/* Springs under feet */}
        <path d="M75 140 L85 142 L75 145 L85 147 L80 150 M115 135 L125 137 L115 140 L125 142 L120 145" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {/* Dashed arrows */}
        <path d="M60 110 Q50 130 55 140" fill="none" stroke="#f97316" strokeWidth="2" strokeDasharray="4 4" strokeLinecap="round" />
        <path d="M50 135 L55 140 L60 135" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M140 130 Q145 110 135 100" fill="none" stroke="#f97316" strokeWidth="2" strokeDasharray="4 4" strokeLinecap="round" />
        <path d="M140 105 L135 100 L130 105" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (key.includes('plank')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        <ellipse cx="100" cy="115" rx="35" ry="12" fill="#f97316" opacity="0.3" />
        <circle cx="150" cy="110" r="10" fill="none" stroke="#e2e8f0" strokeWidth="3" />
        <line x1="140" y1="115" x2="50" y2="130" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
        <path d="M130 116 L130 135 L145 135" fill="none" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M50 130 L45 140 L55 140" fill="none" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="40" y1="145" x2="160" y2="145" stroke="#52525b" strokeWidth="2" />
        <line x1="130" y1="50" x2="170" y2="50" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
        <line x1="130" y1="60" x2="180" y2="60" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
        <path d="M170 42 L180 52 L195 35" fill="none" stroke="#f97316" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (key.includes('nadgarstki')) {
    return (
      <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
        {/* Left Hand */}
        <g stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" fill="none">
          <line x1="75" y1="140" x2="75" y2="100" />
          <line x1="65" y1="140" x2="65" y2="105" />
          <circle cx="85" cy="85" r="8" />
          <path d="M75 100 L60 70 M75 100 L70 65 M75 100 L80 70" />
        </g>
        <path d="M50 140 Q40 120 50 100 Q65 85 95 105 Q105 120 95 140 M95 140 L100 135 M95 140 L90 135" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

        {/* Right Hand */}
        <g stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" fill="none">
          <line x1="125" y1="140" x2="125" y2="100" />
          <line x1="135" y1="140" x2="135" y2="105" />
          <circle cx="115" cy="85" r="8" />
          <path d="M125 100 L140 70 M125 100 L130 65 M125 100 L120 70" />
        </g>
        <path d="M150 140 Q160 120 150 100 Q135 85 105 105 Q95 120 105 140 M105 140 L100 135 M105 140 L110 135" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  // Fallback
  return (
    <svg viewBox="0 0 200 160" className="h-full w-full" aria-hidden>
      <circle cx="100" cy="30" r="20" fill="none" stroke="#f97316" strokeWidth="2" />
      <path d="M100 50 L100 70" stroke="#e2e8f0" strokeWidth="2" />
      <path d="M70 55 L130 55" stroke="#f97316" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
