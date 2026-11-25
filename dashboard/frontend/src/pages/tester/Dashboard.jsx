import StatCards from '../../components/common/StatCards.jsx';
import ModuleDistribution from '../../components/charts/ModuleDistribution.jsx';
import ExecutionsTable from '../../components/tables/ExecutionsTable.jsx';
import Icon from '../../components/common/Icon.jsx';

export default function Dashboard({ stats, modules, runs, selectedModule, onNavigate, onViewAll, onSelectRun }) {
  return (
    <>
      <StatCards stats={stats} />
      <div className={'dashboard-grid' + (selectedModule ? ' module-view' : '')}>
        {!selectedModule && <ModuleDistribution modules={modules} total={stats.total} onSelect={onNavigate} />}
        <section className="panel executions-panel">
          <div className="panel-heading">
            <h2>Recent Executions</h2>
            <button className="text-button" onClick={onViewAll}>View All <Icon name="chevronRight" size={20} /></button>
          </div>
          <ExecutionsTable runs={runs.slice(0, 4)} onSelect={onSelectRun} />
        </section>
      </div>
    </>
  );
}
