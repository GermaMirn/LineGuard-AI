import { Link, useSearchParams } from "react-router-dom";
import AnalysisContent from "@/components/AnalysisContent";
import HistoryContent from "@/components/HistoryContent";

export default function AnalysisPage() {
  const [searchParams] = useSearchParams();
  const currentModel = searchParams.get('model') || 'analysis';

  return (
    <div className="h-screen bg-black text-white flex overflow-hidden relative">
      {/* Декоративные световые элементы */}
      <img
        src="/images/light.svg"
        alt="Light 1"
        className="absolute top-0 left-0 pointer-events-none"
        style={{
          zIndex: 1,
        }}
        loading="eager"
        onError={() => {
          console.error('Failed to load light.svg');
        }}
      />
      <img
        src="/images/light-2.svg"
        alt="Light 2"
        className="absolute bottom-0 right-0 pointer-events-none"
        style={{
          zIndex: 1,
        }}
        loading="eager"
        onError={() => {
          console.error('Failed to load light-2.svg');
        }}
      />

      {/* Левая боковая панель */}
      <div
        className="transition-all duration-300 flex flex-col items-center py-6 w-24"
        style={{ borderRight: '1px solid rgba(255, 255, 255, 0.1)' }}
      >
        {/* Логотип вверху */}
        <img
          src="/images/logo-small.svg"
          alt="LineGuard AI"
          onError={(e) => {
            e.currentTarget.style.display = 'none';
          }}
        />

        {/* Пустое пространство для центрирования навигации */}
        <div className="flex-1"></div>

        {/* Навигация по центру вертикали */}
        <div className="flex flex-col items-center gap-8">
          {/* Анализ */}
          <Link
            to="/panel?model=analysis"
            className="flex flex-col items-center gap-2 p-3"
          >
            <img
              src="/images/analysis.svg"
              alt="analysis"
              className={`rounded-full transition-colors p-[8px] ${
                currentModel === 'analysis'
                  ? 'bg-white/10 hover:bg-white/20'
                  : 'hover:bg-white/10'
              }`}
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            <span className={`text-xs font-medium ${
              currentModel === 'analysis' ? 'text-white' : 'text-white/60'
            }`}>
              АНАЛИЗ
            </span>
          </Link>

          {/* История */}
          <Link
            to="/panel?model=history"
            className="flex flex-col items-center gap-2 p-3"
          >
            <img
              src="/images/history.svg"
              alt="history"
              className={`rounded-full transition-colors p-[8px] ${
                currentModel === 'history'
                  ? 'bg-white/10 hover:bg-white/20'
                  : 'hover:bg-white/10'
              }`}
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            <span className={`text-xs font-medium ${
              currentModel === 'history' ? 'text-white' : 'text-white/60'
            }`}>
              ИСТОРИЯ
            </span>
          </Link>
        </div>

        {/* Пустое пространство для центрирования нижних элементов */}
        <div className="flex-1"></div>

        {/* Нижние элементы */}
        <div className="flex flex-col items-center gap-6">
          {/* Помощь */}
          <button className="p-3 rounded-lg hover:bg-white/10 transition-colors">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="2"/>
              <path d="M9.09 9C9.3251 8.33167 9.78915 7.76811 10.4 7.40913C11.0108 7.05016 11.7289 6.91894 12.4272 7.03871C13.1255 7.15849 13.7588 7.52152 14.2151 8.06353C14.6713 8.60553 14.9211 9.29152 14.92 10C14.92 12 11.92 13 11.92 13M12 17H12.01" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          {/* Аватар */}
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <span className="text-white text-sm font-medium">U</span>
          </div>
        </div>
      </div>

      {/* Основная область */}
      <div className="flex-1 relative overflow-auto">
        {currentModel === 'analysis' ? <AnalysisContent /> : <HistoryContent />}
      </div>
    </div>
  );
}

