import { forwardRef, useContext, useRef } from 'react';
import { getRouterContext, Outlet } from '@tanstack/react-router';
import _ from 'lodash';
import { motion, useIsPresent } from 'motion/react';

const AnimatedOutlet = forwardRef<HTMLDivElement>((_prop, ref) => {
  const RouterContext = getRouterContext();

  const routerContext = useContext(RouterContext);

  const renderedContext = useRef(routerContext);

  const isPresent = useIsPresent();

  if (isPresent) {
    renderedContext.current = _.cloneDeep(routerContext);
  }

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.2 }}
    >
      <RouterContext.Provider value={renderedContext.current}>
        <Outlet />
      </RouterContext.Provider>
    </motion.div>
  );
});

export default AnimatedOutlet;
