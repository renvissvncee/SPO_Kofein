import './header.scss'
import {User2} from 'lucide-react'

const Header = () => {
    return (
        <header className="header">
            <h1 className="header__title">КОФЕИН</h1>
            <button
                className="header__button-profile">
                <User2/>
            </button>
        </header>
    )
}

export default Header;