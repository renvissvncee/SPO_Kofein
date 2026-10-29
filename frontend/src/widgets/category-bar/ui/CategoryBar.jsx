import '../ui/categoryBar.scss'
import { useEffect, useRef } from "react";

const CategoryBar = ({
                         categories,
                         activeCategory,
                         setActiveCategory,
                         isClickScrolling
                     }) => {

    const containerRef = useRef(null);
    const buttonRefs = useRef({});

    // 👉 центрирование активной категории
    useEffect(() => {
        const btn = buttonRefs.current[activeCategory];
        const container = containerRef.current;

        if (btn && container) {
            const containerRect = container.getBoundingClientRect();
            const btnRect = btn.getBoundingClientRect();

            const offset =
                btnRect.left -
                containerRect.left -
                containerRect.width / 2 +
                btnRect.width / 2;

            container.scrollBy({
                left: offset,
                behavior: 'smooth'
            });
        }
    }, [activeCategory]);

    const innerStyle =
        categories.length < 3
            ? { maxWidth: '220px' }
            : { maxWidth: '330px' };

    return (
        <div className="category-bar" ref={containerRef}>
            <div className="category-bar__inner" style={innerStyle}>
                {categories.map(cat => (
                    <button
                        key={cat.id}
                        ref={el => (buttonRefs.current[cat.id] = el)}
                        className={`category-bar__item ${activeCategory === cat.id ? 'active' : ''}`}
                        onClick={() => {
                            isClickScrolling.current = true;
                            setActiveCategory(cat.id);
                        }}
                    >
                        {cat.name}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default CategoryBar;