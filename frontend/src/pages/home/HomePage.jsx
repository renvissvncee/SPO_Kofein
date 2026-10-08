import TimeCard from '../../widgets/time-card/ui/TimeCard';
import FavoriteCoffeehouses from '../../widgets/favorite-coffeehouses/ui/FavoriteCoffeehouses';
import RecentOrders from '../../widgets/recent-orders/ui/RecentOrders';
import './homePage.scss';
import '../../shared/lib/react-bits/glass-surface/GlassSurface.jsx'
import GlassSurface from "../../shared/lib/react-bits/glass-surface/GlassSurface.jsx";

import {api} from "../../shared/api/baseApi.js";
import {useEffect, useState} from "react";
import OrderStatusCard from "../../widgets/order-status-card/ui/OrderStatusCard.jsx";

const HomePage = ({setCurrentPage, currentPage,
                  selectedHourShops, setSelectedHourShops,
                  selectedMinuteShops, setSelectedMinuteShops,
                  selectedDate, setSelectedDate}) => {

    const [currentOrder, setCurrentOrder] = useState(null);

    useEffect(() => {
        const lastOrder = sessionStorage.getItem('lastOrder');
        if (lastOrder) {
            const order = JSON.parse(lastOrder);
            setCurrentOrder(order);
            //sessionStorage.removeItem('lastOrder');
        }
    }, []);

    return (
        <div className="home-page">
            <TimeCard setCurrentPage={setCurrentPage}
                      setSelectedHourShops={setSelectedHourShops}
                      setSelectedMinuteShops={setSelectedMinuteShops}
                      selectedDate={selectedDate}
                      setSelectedDate={setSelectedDate} />

            {/* Карточка заказа появляется здесь, после TimeCard */}
            {currentOrder && <OrderStatusCard order={currentOrder} />}

            <FavoriteCoffeehouses />
        </div>

    );
};

export default HomePage;