import Header from '../../header/ui/Header'
import BottomNavigation from "../../bottom-navigation/ui/BottomNavigtion.jsx";
import './mainLayout.scss'

const MainLayout = ({ children, setCurrentPage, currentPage}) => {
    return (
        <div className="layout">

            <Header setCurrentPage={setCurrentPage} />

            <main className="layout__content">
                {children}
            </main>

            <BottomNavigation currentPage={currentPage} setCurrentPage={setCurrentPage} />
        </div>
    )
}

export default MainLayout