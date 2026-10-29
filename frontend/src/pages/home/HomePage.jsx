import TimeCard from '../../widgets/time-card/ui/TimeCard';
import FavoriteCoffeehouses from '../../widgets/favorite-coffeehouses/ui/FavoriteCoffeehouses';
import RecentOrders from '../../widgets/recent-orders/ui/RecentOrders';
import './homePage.scss';
import '../../shared/lib/react-bits/glass-surface/GlassSurface.jsx'
import GlassSurface from "../../shared/lib/react-bits/glass-surface/GlassSurface.jsx";

import {useState} from "react";
import OrderStatusCard from "../../widgets/order-status-card/ui/OrderStatusCard.jsx";

const HomePage = ({setCurrentPage,
                  setSelectedHourShops,
                  setSelectedMinuteShops,
                  selectedDate, setSelectedDate}) => {

    const [currentOrder] = useState(() => {
        const lastOrder = sessionStorage.getItem('lastOrder');
        return lastOrder ? JSON.parse(lastOrder) : null;
    });

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