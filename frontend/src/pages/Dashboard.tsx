import { useNavigate } from 'react-router-dom';
import { Play, TrendingUp, AlertCircle, Activity } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const mockData = [
  { name: 'Poprawnie', value: 85, color: '#4ade80' },
  { name: 'Błędy', value: 15, color: '#f87171' }
];

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-8 pb-10">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white mb-2">Witaj z powrotem, Trenerze</h2>
          <p className="text-on-surface-variant">Oto podsumowanie twojej ostatniej aktywności.</p>
        </div>
        <button
          onClick={() => navigate('/live')}
          className="flex items-center gap-2 bg-primary text-surface font-bold px-6 py-3 rounded-full hover:bg-primary-container transition-all neon-glow"
        >
          <Play className="w-5 h-5 fill-current" />
          Rozpocznij Analizę Live
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Stat Card 1 */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-medium text-on-surface-variant">Ostatni Trening</h3>
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
              <Activity className="w-5 h-5 text-primary" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white mb-1">85%</div>
          <p className="text-sm text-green-400 flex items-center gap-1">
            <TrendingUp className="w-4 h-4" />
            +5% względem poprzedniego
          </p>
        </div>

        {/* Stat Card 2 */}
        <div className="glass-card rounded-2xl p-6 flex flex-col">
          <h3 className="text-lg font-medium text-on-surface-variant mb-2">Skuteczność Odbicia</h3>
          <div className="flex-1 flex items-center justify-center relative min-h-[120px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={mockData}
                  innerRadius={40}
                  outerRadius={60}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {mockData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex items-center justify-center flex-col">
              <span className="text-2xl font-bold text-white">85%</span>
            </div>
          </div>
        </div>

        {/* AI Recommendations */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-medium text-on-surface-variant mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-primary" />
            Porady AI Coach
          </h3>
          <ul className="flex flex-col gap-4">
            <li className="bg-surface-variant/40 rounded-lg p-3 border border-white/5">
              <p className="text-sm text-white font-medium mb-1">Popraw ugięcie kolan</p>
              <p className="text-xs text-on-surface-variant">W 30% przypadków kolana były zbyt proste.</p>
            </li>
            <li className="bg-surface-variant/40 rounded-lg p-3 border border-white/5">
              <p className="text-sm text-white font-medium mb-1">Stabilność rąk</p>
              <p className="text-xs text-on-surface-variant">Świetna praca ramion podczas odbioru.</p>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
