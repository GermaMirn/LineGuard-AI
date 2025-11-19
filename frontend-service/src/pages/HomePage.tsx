import { Link } from "react-router-dom";
import { Button } from "@heroui/react";
import { motion } from "framer-motion";


export default function HomePage() {
  return (
    <div className="h-screen bg-black text-white relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none" style={{ overflow: 'visible', zIndex: 0 }}>
        {/* Сетка на фоне через SVG - сзади, по центру */}
        <img
          src="/images/grid.svg"
          alt="Grid"
          className="absolute left-1/2"
          style={{
            top: '65%',
            transform: 'translateX(-50%) translateY(-50%)',
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: 1,
            zIndex: 9999,
          }}
        />

        {/* Луч света через SVG - максимальный приоритет */}
        <img
          src="/images/ray.svg"
          alt="Light beam"
          className="absolute top-0 left-12"
          style={{
            width: '200%',
            height: '200%',
            objectFit: 'none',
            objectPosition: 'top left',
            mixBlendMode: 'screen',
            zIndex: 999,
          }}
        />

        {/* Scope по центру */}
        <img
          src="/images/scope.svg"
          alt="Scope"
          className="absolute left-1/2"
          style={{
            top: '65%',
            transform: 'translateX(-50%) translateY(-50%)',
            zIndex: 2,
          }}
        />
      </div>

      {/* Обертка для всего контента */}
      <div className="relative z-10" style={{ padding: '40px' }}>
        {/* Навигация */}
        <div className="w-full flex items-center justify-between">
          {/* Логотип слева */}
          <div className="flex items-center gap-3">
            <img
              src="/images/logo-small.svg"
              alt="LineGuard AI"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            <span className="text-white text-xl font-bold">LineGuard AI</span>
          </div>

          {/* Навигационные ссылки по центру */}
          <div
            className="hidden sm:flex gap-[42px] border border-white/10 pl-[24px] pt-[18px] pb-[18px] pr-[24px] ml-[120px] rounded-[8px]"
            style={{ textShadow: '0 0 10px rgba(255, 255, 255, 0.5), 0 0 20px rgba(255, 255, 255, 0.7)' }}
          >
            <Link
              to="/"
              className="text-white font-medium"
            >
              Главная
            </Link>
            <Link
              to="/panel?model=analysis"
              className="transition-colors font-medium hover:!text-white"
              style={{ color: 'rgba(255, 255, 255, 0.6)' }}
            >
              Анализ
            </Link>
            <Link
              to="/panel?model=history"
              className="transition-colors font-medium hover:!text-white"
              style={{ color: 'rgba(255, 255, 255, 0.6)' }}
            >
              История
            </Link>
          </div>

          {/* Кнопки справа */}
          <div className="flex items-center gap-4">
            <Button
              as={Link}
              variant="bordered"
              className="text-white pt-[8px] pb-[8px] pl-[26px] pr-[26px]"
              style={{ backgroundColor: '#262438', borderRadius: '8px', color: '#FFFFFF', fontWeight: 550}}
              radius="full"
            >
              Войти
            </Button>
            <Button
              as={Link}
              variant="bordered"
              className="text-white pt-[6px] pb-[8px] pl-[11px] pr-[12px]"
              style={{
                border: '1px solid #FFFFFF',
                borderRadius: '8px',
                color: '#FFFFFF',
                fontWeight: 650
              }}
              radius="full"
            >
              Зарегистрироваться
            </Button>
          </div>
        </div>

        {/* Основной контент */}
        <div className="flex flex-col items-center justify-center h-[calc(100vh-120px)] px-4">
        <div className="max-w-6xl mx-auto flex flex-col items-center">
          {/* Центральная графика - заглушка для изображения */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, ease: "easeOut" }}
            className="flex justify-center mb-9"
            style={{ marginTop: '28vh' }}
          >
            <div className="relative flex items-center justify-center">
              {/* Логотип по центру */}
              <img
                src="/images/LOGO.png"
                alt="LineGuard AI Logo"
                className="max-w-full h-[128px] w-[128px]"
                style={{ boxShadow: '0 0 70px rgba(99, 88, 255, 1)', borderRadius: '28px' }}
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
            </div>
          </motion.div>

          {/* Текстовый контент - прямо под логотипом */}
          <motion.div
            initial={{ opacity: 0, y: 0 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="text-center mb-8"
          >
            <h1
              className="text-6xl md:text-7xl mb-4"
              style={{
                fontWeight: 400,
                background: 'linear-gradient(to right, #FFFFFF 0%, #BFB8FA 21%, #FFFFFF 65%, #8780EB 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}
            >
              Анализ, который <br/> не дает сбоям шанса
            </h1>
            <p className="text-gray-300 max-w-3xl mx-auto leading-relaxed mb-6 w-[516px] h-[52px]" style={{ fontSize: '16px' }}>
              Компьютерное зрение для точного анализа состояния линий электропередачи и оптимизации технического обслуживания.
            </p>
          </motion.div>

          {/* Кнопка CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="flex justify-center"
            style={{ marginTop: '-40px' }}
          >
            <Button
              as={Link}
              to="/panel?model=analysis"
              size="lg"
              className="text-white font-bold text-lg rounded-full hover:scale-105 transition-all duration-300 flex items-center justify-center border border-white/60 h-[42px]"
              radius="full"
              style={{
                padding: '13px 12px',
                backgroundColor: 'rgba(88, 75, 255, 0.4)',
                fontWeight: 400
              }}
            >
              <img src="/images/ai-point.svg" alt="AI Point" />
              Попробовать анализ
            </Button>
          </motion.div>
        </div>
      </div>
      </div>
    </div>
  );
}
