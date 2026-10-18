import { ChatView } from "./components/chat/ChatView";

/**
 * EvidHist 对话：当前版本只暴露对话主界面（史料工作台视图暂不显示入口），
 * 材料与论断仍由对话内的工具读写，界面不直接呈现。
 */
export function App() {
  return (
    <main className="app">
      <h1 className="visually-hidden">EvidHist 对话</h1>
      <ChatView />
    </main>
  );
}
