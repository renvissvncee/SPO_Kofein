import '../shop/shopPage.scss'
import { useEffect, useRef, useState } from "react";

import ShopHeader from "../../widgets/shop-header/ui/ShopHeader.jsx";
import CategoryBar from "../../widgets/category-bar/ui/CategoryBar.jsx";
import MenuList from "../../widgets/menu-list/ui/MenuList.jsx";
import { api } from "../../shared/api/baseApi.js";
import {Clock, Coffee} from 'lucide-react';

const ShopPage = ({ selectedShop, setCurrentPage }) => {
    const scrollRef = useRef(null);
    const headerRef = useRef(null);
    const stickyRef = useRef(null);

    const [isCollapsed, setIsCollapsed] = useState(false);
    const [menu, setMenu] = useState([]);
    const [loading, setLoading] = useState(false);
    const [activeCategory, setActiveCategory] = useState('');

    const [stickyTop, setStickyTop] = useState(280);

    const [totalSum, setTotalSum] = useState(0);

    const isClickScrolling = useRef(false);

    useEffect(() => {
        const el = scrollRef.current;
        if (!el) return;

        const handleScroll = () => {
            const scrollTop = el.scrollTop;

            // диапазон схлопывания
            const max = 280;
            const min = 100;

            // сколько "сжали"
            const progress = Math.min(scrollTop / 180, 1);

            const currentTop = max - (max - min) * progress;

            setStickyTop(currentTop);
        };

        el.addEventListener('scroll', handleScroll);
        return () => el.removeEventListener('scroll', handleScroll);
    }, []);

    const loadMenu = async (id) => {
        try {
            setLoading(true);
            const data = await api.getCoffeeShopMenu(id);
            setMenu(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            setMenu([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (selectedShop?.id) loadMenu(selectedShop.id);
    }, [selectedShop?.id]);

    useEffect(() => {
        if (menu.length > 0) setActiveCategory(menu[0].id);
    }, [menu]);

    useEffect(() => {
        const el = scrollRef.current;
        if (!el) return;

        let ticking = false;
        const THRESHOLD = 20;

        const handleScroll = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    const next = el.scrollTop > THRESHOLD;
                    setIsCollapsed(prev => (prev === next ? prev : next));
                    ticking = false;
                });
                ticking = true;
            }
        };

        setIsCollapsed(el.scrollTop > THRESHOLD);
        el.addEventListener('scroll', handleScroll);
        return () => el.removeEventListener('scroll', handleScroll);
    }, []);

    if (!selectedShop) return <div>loading...</div>;

    const categories = menu.map(category => ({
        id: category.id,
        name: category.name,
        items: category.items
    }));

    return (
        <div className="shop">
            <div className="scroll" ref={scrollRef}>

                <div className="sticky-header">
                <ShopHeader
                    shop={selectedShop}
                    setCurrentPage={setCurrentPage}
                    headerRef={headerRef}
                    isCollapsed={isCollapsed}
                />
                </div>

                {/* CategoryBar с sticky */}
                <div className="sticky"
                     ref={stickyRef}
                     style={{ top: `${stickyTop}px` }}>
                    <CategoryBar
                        categories={categories}
                        activeCategory={activeCategory}
                        setActiveCategory={setActiveCategory}
                        isClickScrolling={isClickScrolling}
                    />
                </div>

                {loading && <div>Загрузка меню...</div>}

                {/* MenuList теперь получает scrollRef и stickyRef */}
                <MenuList
                    selectedShop={selectedShop}
                    setCurrentPage={setCurrentPage}
                    categories={categories}
                    activeCategory={activeCategory}
                    setActiveCategory={setActiveCategory}
                    scrollRef={scrollRef}
                    stickyRef={stickyRef}
                    isClickScrolling={isClickScrolling}
                    totalSum={totalSum}
                    setTotalSum={setTotalSum}
                />



            </div>
        </div>
    );
};

export default ShopPage;