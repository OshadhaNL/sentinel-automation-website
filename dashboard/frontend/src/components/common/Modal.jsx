import { useEffect, useRef } from 'react';
import Icon from './Icon.jsx';

export default function Modal({ title, children, onClose, wide = false }) {
  const dialog = useRef(null);

  useEffect(() => {
    const element = dialog.current;
    const previousFocus = document.activeElement;
    element.showModal();
    return () => {
      element.close();
      previousFocus?.focus();
    };
  }, []);

  return (
    <dialog ref={dialog} className={'modal' + (wide ? ' modal-wide' : '')}
      aria-labelledby="modal-title"
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="modal-heading">
        <h2 id="modal-title">{title}</h2>
        <button className="icon-button" onClick={onClose} aria-label="Close dialog"><Icon name="close" /></button>
      </div>
      {children}
    </dialog>
  );
}
