import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

const CustomDropdown = ({
  options,
  placeholder = "Select an option",
  value,
  onChange,
  className = "",
  pushContent = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedValue, setSelectedValue] = useState(value || "");
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    setSelectedValue(value || "");
  }, [value]);

  const handleSelect = (optionValue, optionLabel) => {
    setSelectedValue(optionValue);
    setIsOpen(false);
    if (onChange) {
      onChange(optionValue);
    }
  };

  const getSelectedLabel = () => {
    const selected = options.find((opt) => opt.value === selectedValue);
    return selected ? selected.label : placeholder;
  };

  const springConfig = {
    type: "spring",
    stiffness: 260,
    damping: 24,
    mass: 0.9,
  };

  const chevronSpring = {
    type: "spring",
    stiffness: 220,
    damping: 20,
  };

  return (
    <div
      className={`dash-select-wrapper ${className} ${isOpen ? "open" : ""} ${
        isOpen && pushContent ? "dropdown-open" : ""
      }`}
      ref={dropdownRef}
    >
      <motion.div
        className={`dash-select ${isOpen ? "open" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
        whileTap={{ scale: 0.98 }}
        transition={springConfig}
      >
        <span>{getSelectedLabel()}</span>
        <motion.div
          className="dash-select-chevron"
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={chevronSpring}
        />
      </motion.div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="dash-dropdown open"
            initial={{
              opacity: 0,
              scale: 0.95,
              y: -8,
            }}
            animate={{
              opacity: 1,
              scale: 1,
              y: 0,
            }}
            exit={{
              opacity: 0,
              scale: 0.95,
              y: -8,
            }}
            transition={springConfig}
            style={{ transformOrigin: "top" }}
          >
            {options.map((option, index) => (
              <motion.div
                key={option.value}
                className={`dash-option ${
                  selectedValue === option.value ? "selected" : ""
                }`}
                onClick={() => handleSelect(option.value, option.label)}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  ...springConfig,
                  delay: index * 0.05,
                }}
                whileTap={{ scale: 0.98 }}
              >
                {option.label}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CustomDropdown;
