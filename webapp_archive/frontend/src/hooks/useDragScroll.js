import { useRef } from 'react';

export function useDragScroll() {
  const ref = useRef(null);
  const isDraggingRef = useRef(false);

  const handleMouseDown = (e) => {
    const ele = ref.current;
    if (!ele) return;
    ele.isDown = true;
    ele.startY = e.pageY - ele.offsetTop;
    ele.scrollTopInit = ele.scrollTop;
    isDraggingRef.current = false;
  };

  const handleMouseLeave = () => {
    const ele = ref.current;
    if (!ele) return;
    ele.isDown = false;
  };

  const handleMouseUp = () => {
    const ele = ref.current;
    if (!ele) return;
    ele.isDown = false;
  };

  const handleMouseMove = (e) => {
    const ele = ref.current;
    if (!ele || !ele.isDown) return;
    e.preventDefault();
    const y = e.pageY - ele.offsetTop;
    const walk = (y - ele.startY); 
    if (Math.abs(walk) > 5) {
      isDraggingRef.current = true;
    }
    ele.scrollTop = ele.scrollTopInit - (walk * 1.5);
  };

  const handleClick = (e) => {
    if (isDraggingRef.current) {
      e.stopPropagation();
      e.preventDefault();
    }
  };

  return {
    ref,
    onMouseDown: handleMouseDown,
    onMouseLeave: handleMouseLeave,
    onMouseUp: handleMouseUp,
    onMouseMove: handleMouseMove,
    onClickCapture: handleClick,
  };
}
