import './recentOrders.scss';

const RecentOrders = () => {
    return (
        <div className="recent-orders">
            <h2 className="recent-orders__title">Неделя заказов</h2>
            <div className="recent-orders__content">
                {/* Здесь будет контент с заказами за неделю */}
                <p className="recent-orders__empty">Нет заказов</p>
            </div>
        </div>
    );
};

export default RecentOrders;