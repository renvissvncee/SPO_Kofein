import React, { useRef, useState } from 'react';
import './promoSlider.scss';

const PromoSlider = () => {
    const [scrollPosition, setScrollPosition] = useState(0);
    const sliderRef = useRef(null);

    const promos = [
        {
            id: 1,
            title: "Когда хочется на юга",
            subtitle: "Кофе с ароматом лета",
            emoji: "☀️",
            gradient: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            color: "#667eea"
        },
        {
            id: 2,
            title: "Карманная новинка",
            subtitle: "Пробуй первым!",
            emoji: "🆕",
            gradient: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
            color: "#f5576c"
        },
        {
            id: 3,
            title: "Откройте заряд настроения",
            subtitle: "Энергия на весь день",
            emoji: "⚡",
            gradient: "linear-gradient(135deg, #fa709a 0%, #fee140 100%)",
            color: "#fa709a"
        },
        {
            id: 4,
            title: "Первый заказ для коллег со скидкой",
            subtitle: "-20% на первый заказ",
            emoji: "👥",
            gradient: "linear-gradient(135deg, #30cfd0 0%, #330867 100%)",
            color: "#30cfd0"
        },
        {
            id: 5,
            title: "Работа в Додо",
            subtitle: "Присоединяйся к команде",
            emoji: "💼",
            gradient: "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)",
            color: "#a8edea"
        },
        {
            id: 6,
            title: "Какая вы пицца?",
            subtitle: "Пройди тест",
            emoji: "🍕",
            gradient: "linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)",
            color: "#fcb69f"
        },
        {
            id: 7,
            title: "До по...",
            subtitle: "Скоро открытие",
            emoji: "🎉",
            gradient: "linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)",
            color: "#ff9a9e"
        }
    ];

    const scroll = (direction) => {
        const container = sliderRef.current;
        const scrollAmount = 300;

        if (direction === 'left') {
            container.scrollLeft -= scrollAmount;
        } else {
            container.scrollLeft += scrollAmount;
        }

        // Обновляем позицию для показа/скрытия кнопок
        setTimeout(() => {
            setScrollPosition(container.scrollLeft);
        }, 100);
    };

    const handleScroll = () => {
        setScrollPosition(sliderRef.current.scrollLeft);
    };

    const showLeftButton = scrollPosition > 0;
    const showRightButton = sliderRef.current
        ? scrollPosition < sliderRef.current.scrollWidth - sliderRef.current.clientWidth - 10
        : true;

    return (
        <div className="promo-slider">
            <div
                className="promo-slider__track"
                ref={sliderRef}
                onScroll={handleScroll}
            >
                {promos.map((promo) => (
                    <div key={promo.id} className="promo-slider__card">
                        <div
                            className="promo-slider__card-gradient"
                            style={{ background: promo.gradient }}
                        >
                            <div className="promo-slider__card-emoji">{promo.emoji}</div>
                        </div>
                        <div className="promo-slider__card-content">
                            <h4 className="promo-slider__card-title">{promo.title}</h4>
                            <p className="promo-slider__card-subtitle">{promo.subtitle}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default PromoSlider;