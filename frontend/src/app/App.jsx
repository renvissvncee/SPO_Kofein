import './globals.css';

import MainLayout from "../widgets/main-layout/ui/MainLayout.jsx";

import HomePage from '../pages/home/HomePage';
import ShopsPage from '../pages/shops/ShopsPage';
import {useState} from "react";
import ShopPage from "../pages/shop/ShopPage.jsx";
import ScrollableContainer from "../widgets/ScrollableContainer.jsx";
//import FavoritesPage from '../pages//FavoritesPage';
//import OrdersPage from './pages/OrdersPage';
//import ProfilePage from './pages/ProfilePage';

function App() {

    // Какая страница открыта
    const [currentPage, setCurrentPage] = useState('home');

    // Какая выбрана кофейня на странице 'shops'
    const [selectedShop, setSelectedShop] = useState(null);

    // Какое время выбрано на TimeCard на странице 'home'
    const [selectedHourShops, setSelectedHourShops] = useState(null);
    const [selectedMinuteShops, setSelectedMinuteShops] = useState(null);

    // Какая дата выбрана на Календаре
    const date = new Date();
    const [selectedDate, setSelectedDate] = useState(date);

    const renderPage = () => {
        switch (currentPage) {
            case 'home':
                return <HomePage setCurrentPage={setCurrentPage}
                                 currentPage={currentPage}
                                 selectedHourShops={selectedHourShops}
                                 setSelectedHourShops={setSelectedHourShops}
                                 selectedMinuteShops={selectedMinuteShops}
                                 setSelectedMinuteShops={setSelectedMinuteShops}
                                 setSelectedDate={setSelectedDate}
                                 selectedDate={selectedDate}
                                    />;
            case 'shops':
                return <ShopsPage setCurrentPage={setCurrentPage}
                                  setSelectedShop={setSelectedShop}
                                  selectedHourShops={selectedHourShops}
                                  setSelectedHourShops={setSelectedHourShops}
                                  selectedMinuteShops={selectedMinuteShops}
                                  selectedDate={selectedDate}
                                  setSelectedDate={setSelectedDate}
                                  setSelectedMinuteShops={setSelectedMinuteShops}/>;
            case 'shop':
                return (
                    <ScrollableContainer>
                        <ShopPage setCurrentPage={setCurrentPage} selectedShop={selectedShop} />
                    </ScrollableContainer>
                );
            default:
                return <HomePage setCurrentPage={setCurrentPage}
                                 currentPage={currentPage}
                                 selectedHourShops={selectedHourShops}
                                 setSelectedHourShops={setSelectedHourShops}
                                 selectedMinuteShops={selectedMinuteShops}
                                 setSelectedMinuteShops={setSelectedMinuteShops}
                                 setSelectedDate={setSelectedDate}
                                 selectedDate={selectedDate} />;
        }
    };

    // если страница 'shop' — не оборачиваем в MainLayout
    if (currentPage === 'shop') {
        return renderPage(); // без MainLayout
    }

    return (
        <MainLayout currentPage={currentPage} setCurrentPage={setCurrentPage}>
            {renderPage()}
        </MainLayout>
    );
}


export default App;