export default function WindowWrapper({ children, ...rest }) {
  return (
    <div
      {...rest}
      style={{
        position: "relative",
        display: "block",
        width: "100vw",
        height: "100vh",
        background: "transparent",
      }}
    >
      {children}
    </div>
  );
}
