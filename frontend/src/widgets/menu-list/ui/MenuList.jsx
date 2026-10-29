import './menuList.scss';
import ProductCover from "../../../shared/icons/assets/product_cover.png";
import {useCallback, useEffect, useRef, useState} from "react";

import GlassSurface from "../../../shared/lib/react-bits/glass-surface/GlassSurface.jsx";
import {api} from "../../../shared/api/baseApi.js";

import {LucideShoppingBag} from 'lucide-react'

import {X, Check} from 'lucide-react'


const MenuList = ({
                      categories,
                      activeCategory,
                      setActiveCategory,
                      scrollRef,
                      stickyRef,
                      isClickScrolling,
                      totalSum,
                      setTotalSum,
                      selectedShop,
                      setCurrentPage
                  }) => {

    // Функция оформления заказа (без API)
    const handleCheckout = () => {
        if (cartItems.length === 0) return;

        // Получаем выбранное время (если есть)
        const savedHour = localStorage.getItem('selectedHour');
        const savedMinute = localStorage.getItem('selectedMinute');
        const timeText = savedHour && savedMinute
            ? `Сегодня, к ${savedHour}:${savedMinute.toString().padStart(2, '0')}`
            : "Сегодня, к 9:00";

        // Сохраняем заказ
        sessionStorage.setItem('lastOrder', JSON.stringify({
            shopName: selectedShop?.name || 'M-Coffee',
            totalAmount: totalSum,
            timeText: timeText,
            timestamp: Date.now()
        }));

        // Очищаем корзину
        setCartItems([]);
        setTotalSum(0);
        setIsCartOpen(false);

        // Переходим на главную
        if (setCurrentPage) {
            setCurrentPage('home');
        }
    };



    const [isCartOpen, setIsCartOpen] = useState(false);
    const [cartItems, setCartItems] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isUpdating, setIsUpdating] = useState(false); // для блокировки во время обновления


    const categoryRefs = useRef({});

    const tg_id = 0;

    // выбранные товары
    const [clickedItems, setClickedItems] = useState({});

    // 👉 СИНХРОНИЗАЦИЯ ПРИ СКРОЛЛЕ
    useEffect(() => {
        const container = scrollRef.current;
        const sticky = stickyRef.current;

        if (!container || !sticky) return;

        const handleScroll = () => {
            if (isClickScrolling.current) return;

            const isAtTop = container.scrollTop === 0;

            if (isAtTop) {
                const firstCategoryId = Object.keys(categoryRefs.current)[0];
                if (firstCategoryId && activeCategory !== firstCategoryId) {
                    setActiveCategory(firstCategoryId);
                }
                return;
            }

            let current = null;
            let minDiff = Infinity;

            const stickyRect = sticky.getBoundingClientRect();
            const targetY = stickyRect.bottom;

            Object.entries(categoryRefs.current).forEach(([id, el]) => {
                if (!el) return;

                const rect = el.getBoundingClientRect();
                const diff = Math.abs(rect.top - targetY);

                if (diff < minDiff) {
                    minDiff = diff;
                    current = id;
                }
            });

            if (current && current !== activeCategory) {
                setActiveCategory(current);
            }
        };

        container.addEventListener('scroll', handleScroll);
        return () => container.removeEventListener('scroll', handleScroll);
    }, []);

    // 👉 СКРОЛЛ ПРИ КЛИКЕ
    useEffect(() => {
        if (!isClickScrolling.current) return;

        const container = scrollRef.current;
        const el = categoryRefs.current[activeCategory];
        const sticky = stickyRef.current;

        if (!container || !el || !sticky) return;

        const headerHeight = container.querySelector('.shop-header')?.offsetHeight || 0;
        const OFFSET = sticky.offsetHeight + (headerHeight - 170);

        container.scrollTo({
            top: el.offsetTop - OFFSET,
            behavior: 'smooth'
        });

        const timeout = setTimeout(() => {
            isClickScrolling.current = false;
        }, 400);

        return () => clearTimeout(timeout);
    }, [activeCategory]);

    // Увелиичение количества товара в корзине
// 👉 Увеличение количества
    const handleIncrease = async (item) => {
        if (isUpdating) return;
        setIsUpdating(true);

        // Оптимистичное обновление
        const newQuantity = item.quantity + 1;
        const newTotalPrice = item.price * newQuantity;
        updateCartItemOptimistically(item.id, newQuantity, newTotalPrice);

        try {
            const updatedCart = await api.addToCart({
                tg_id: tg_id,
                coffee_shop_id: selectedShop.id,
                menu_item_id: item.menu_item_id,
                quantity: 1
            });

            if (updatedCart?.items) {
                const updatedItem = updatedCart.items.find(i => i.id === item.id);
                if (updatedItem) {
                    setCartItems(prev => prev.map(i =>
                        i.id === item.id
                            ? {
                                ...i,
                                quantity: updatedItem.quantity,
                                total_price: updatedItem.total_price
                            }
                            : i
                    ));
                    setTotalSum(updatedCart.total_amount);
                }
            }
        } catch (e) {
            console.error("Increase ERROR:", e);
            await loadCart();
        } finally {
            setIsUpdating(false);
        }
    };

    // Уменьшение количества товара в корзине
// 👉 Уменьшение количества
    // 👉 Уменьшение количества (исправленный)
    const handleDecrease = async (item) => {
        if (isUpdating) return;
        setIsUpdating(true);

        const newQuantity = item.quantity - 1;

        if (newQuantity === 0) {
            // Оптимистичное удаление
            const deletedItemPrice = item.total_price;
            setCartItems(prev => prev.filter(i => i.id !== item.id));
            setTotalSum(prev => prev - deletedItemPrice);

            try {
                console.log("Deleting item:", { tg_id, order_item_id: item.id });
                await api.deleteFromCart(tg_id, item.id);
                // Не вызываем loadCart, чтобы не дергаться
            } catch (e) {
                console.error("Delete ERROR:", e);
                // Откат при ошибке - перезагружаем корзину
                await loadCart();
            }
        } else {
            // Оптимистичное обновление
            const newTotalPrice = item.price * newQuantity;
            updateCartItemOptimistically(item.id, newQuantity, newTotalPrice);

            try {
                const updatedCart = await api.addToCart({
                    tg_id: tg_id,
                    coffee_shop_id: selectedShop.id,
                    menu_item_id: item.menu_item_id,
                    quantity: -1
                });

                // Синхронизируем с сервером
                if (updatedCart?.items) {
                    const updatedItem = updatedCart.items.find(i => i.id === item.id);
                    if (updatedItem) {
                        setCartItems(prev => prev.map(i =>
                            i.id === item.id
                                ? {
                                    ...i,
                                    quantity: updatedItem.quantity,
                                    total_price: updatedItem.total_price
                                }
                                : i
                        ));
                        setTotalSum(updatedCart.total_amount);
                    }
                }
            } catch (e) {
                console.error("Decrease ERROR:", e);
                await loadCart(); // откат при ошибке
            }
        }

        setIsUpdating(false);
    };
    // Функция загрузки корзины
    const loadCart = useCallback(async () => {
        if (!selectedShop?.id) return;

        setIsLoading(true);
        try {
            const data = await api.getCart(tg_id, selectedShop.id);
            console.log("Cart Response:", data);

            if (data && data.items !== undefined) {
                setTotalSum(data.total_amount || 0);
                const normalizedItems = (data.items || []).map(item => ({
                    id: item.id,
                    menu_item_id: item.menu_item_id,
                    name: item.product.name,
                    description: item.product.description,
                    quantity: item.quantity,
                    price: item.unit_price,
                    total_price: item.total_price,
                    image_url: item.product.image_url
                }));
                setCartItems(normalizedItems);
            } else {
                setTotalSum(0);
                setCartItems([]);
            }
        } catch (e) {
            console.error("GetCart ERROR:", e.response?.data || e.message);
            setCartItems([]);
            setTotalSum(0);
        } finally {
            setIsLoading(false);
        }
    }, [selectedShop?.id, tg_id, setTotalSum]);

// 👉 Оптимистичное обновление UI (исправленная версия)
    const updateCartItemOptimistically = useCallback((itemId, newQuantity, newTotalPrice) => {
        setCartItems(prevItems => {
            const oldItem = prevItems.find(i => i.id === itemId);
            const oldTotalPrice = oldItem?.total_price || 0;

            const updatedItems = prevItems.map(item =>
                item.id === itemId
                    ? { ...item, quantity: newQuantity, total_price: newTotalPrice }
                    : item
            ).filter(item => item.quantity > 0);

            // Обновляем общую сумму
            setTotalSum(prev => prev + (newTotalPrice - oldTotalPrice));

            return updatedItems;
        });
    }, []);



    // Обработчик добавления товара
    const handleClickMenuItem = async (item) => {
        console.log("Adding item:", item.id);

        setClickedItems(prev => ({ ...prev, [item.id]: true }));
        setTimeout(() => setClickedItems(prev => ({ ...prev, [item.id]: false })), 600);

        try {
            const updatedCart = await api.addToCart({
                tg_id: tg_id,
                coffee_shop_id: selectedShop.id,
                menu_item_id: item.id,
                quantity: 1
            });

            console.log("AddToCart Response:", updatedCart);

            if (updatedCart && updatedCart.items !== undefined) {
                setTotalSum(updatedCart.total_amount || 0);
                const normalizedItems = (updatedCart.items || []).map(item => ({
                    id: item.id,
                    menu_item_id: item.menu_item_id,
                    name: item.product.name,
                    description: item.product.description,
                    quantity: item.quantity,
                    price: item.unit_price,
                    total_price: item.total_price,
                    image_url: item.product.image_url
                }));
                setCartItems(normalizedItems);
            } else {
                await loadCart();
            }
        } catch (err) {
            console.error("AddToCart ERROR:", err.response?.data || err.message);
        }
    };

    // Загружаем корзину при выборе магазина
    useEffect(() => {
        loadCart();
    }, [selectedShop?.id]);

    const hasItems = totalSum > 0;

    return (
        <div className="menu-list">
            {categories.map((category) => (
                <div
                    key={category.id}
                    ref={el => (categoryRefs.current[category.id] = el)}
                    className="menu-list__section"
                >
                    <h2 className="menu-list__title">
                        {category.name}
                    </h2>

                    <div className="menu-list__items">
                        {category.items.map((item) => (
                            <div key={item.id} className="menu-item">
                                <div className="menu-item__image-wrapper">
                                    <img
                                        src={item.image_url || ProductCover}
                                        alt={item.name}
                                        className="menu-item__image"
                                    />
                                </div>

                                <div className="menu-item__info">
                                    <p className="menu-item__name">
                                        {item.name}
                                    </p>

                                    <button
                                        className={`menu-item__price ${clickedItems[item.id] ? 'added' : ''}`}
                                        onClick={() => handleClickMenuItem(item)}
                                    >
                                        {clickedItems[item.id] ? <Check /> : `+${item.base_price} ₽`}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}

            {hasItems && (
                <GlassSurface
                    className='glass-cart'
                    width={'auto'}
                    height={45}
                    borderRadius={40}
                    backgroundOpacity={0.2}
                    opacity={1}
                    brightness={135}
                    displace={1}
                    distortionScale={-20}
                    saturation={0.5}
                    redOffset={0}
                    greenOffset={2}
                    blueOffset={4}
                    mixBlendMode="normal"
                    style={{
                        position: 'fixed',
                        bottom: '5%',
                        right: '10%',
                        transition: 'transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)',
                        zIndex: 10,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '0 12px',
                        backgroundColor: 'rgba(0,0,0,0.6)',
                    }}
                >
                    <div className='cart-container' onClick={() => setIsCartOpen(true)}>
                        <LucideShoppingBag size={20} color={'white'}/>
                        <span className="glass-cart__sum">{totalSum} ₽</span>
                    </div>
                </GlassSurface>
            )}

            {isCartOpen && (
                <div className="cart-sheet" >
                    <div className="cart-sheet__overlay" onClick={() => setIsCartOpen(false)}/>

                    <div className="cart-sheet__content">
                        <div className="cart-sheet__header">
                            <p className="cart-sheet__title">{selectedShop?.name || 'Корзина'}</p>
                            <button className="cart-sheet__buttons" onClick={() => setIsCartOpen(false)}>
                                <X />
                            </button>
                        </div>

                        <div className="cart-sheet__items">
                            {isLoading ? (
                                <div className="cart-loading">Загрузка...</div>
                            ) : cartItems.length === 0 ? (
                                <div className="cart-empty">Корзина пуста</div>
                            ) : (
                                cartItems.map((item, index) => (
                                    <div key={item.id || index} className="cart-item">
                                        <div className="cart-item__left">
                                            <div className="cart-item__image-wrapper">
                                                <img
                                                    src={item.image_url || ProductCover}
                                                    alt={item.name}
                                                    className="menu-item__image"
                                                />
                                            </div>

                                            <div className="cart-item__info">
                                                <p className="cart-item__name">{item.name}</p>
                                                {item.description && (
                                                    <p className="cart-item__desc">{item.description}</p>
                                                )}
                                                <div className="cart-item__controls">
                                                    <button className="cart-btn"
                                                            onClick={() => handleDecrease(item)}
                                                    >
                                                        −
                                                    </button>
                                                    <span className="cart-qty">{item.quantity}</span>
                                                    <button className="cart-btn"
                                                            onClick={() => handleIncrease(item)}
                                                    >
                                                        +
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="cart-item__right">
                                            <span className="cart-item__price">{item.total_price} ₽</span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        {cartItems.length > 0 && (
                            <div className="cart-sheet__footer">
                                <button className="cart-sheet__checkout"
                                        onClick={handleCheckout}
                                >
                                    Оформить заказ • {totalSum} ₽
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default MenuList;