import React from 'react';
import { Newspaper, FileWarning, MapPin, BarChart2, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

// Container stagger configuration
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.12,
    },
  },
};

// Box Pop-Up (Scale & Spring) animation variant
const popUpCardVariants = {
  hidden: { 
    opacity: 0, 
    scale: 0.85, 
  },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 1.2,
      ease: [0.6, 1, 0.3, 1],
    },
  },
};

export const BottomActionCards = ({ onNavigate }) => {
  return (
    <section className="w-full max-w-7xl mx-auto px-4 sm:px-6 pt-2 pb-12 sm:pb-16 overflow-hidden">
     
    </section>
  );
};