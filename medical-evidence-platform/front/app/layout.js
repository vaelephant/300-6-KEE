import './style.css';
import {SessionProvider} from './Session';
export const metadata={title:'DrSeek · 证据查询工作台',description:'医疗数据查询与来源核对'};
export default function Layout({children}){return <html lang="zh-CN"><body><SessionProvider>{children}</SessionProvider></body></html>}
