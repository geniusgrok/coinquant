from pathlib import Path
p=Path('/workspace/btc-alpha-beta-improve/coinquant/tests/test_edge_forward.py');s=p.read_text()
needle='    def enter(self):\n'
helpers='''    def macro_receipt(self, stamp, *, eligible=True):
        # SYNTHETIC official-shaped retained ALFRED bytes, parsed by the real adapter.
        today = f.datetime.fromtimestamp(stamp / 1000, f.timezone.utc).date()
        vintage = today - f.timedelta(days=4)
        dates = [vintage - f.timedelta(days=20-i) for i in range(21)]
        form = ('<select id="form_selected_vintage_dates">' + ''.join('<option value="' + str(v) + '">' for v in dates) + '</select>').encode()
        form_path = self.root / ('macro-form-' + str(self.serial) + '.html'); form_path.write_bytes(form)
        out = io.StringIO(); writer = f.csv.writer(out)
        writer.writerow(['observation_date'] + [v.strftime('DFII10_%Y%m%d') for v in dates])
        for i in range(21):
            writer.writerow([str(today - f.timedelta(days=26-i))] + [''] * 20 + [str(D('2') - D(i)/40 if eligible else D('2'))])
        archive = io.BytesIO()
        with ZipFile(archive, 'w') as z: z.writestr('DFII10.csv', out.getvalue())
        receipt = self.receipt(f.DFII_URL, archive.getvalue(), stamp - 100, raw=True)
        receipt.update(form_path=str(form_path), form_sha256=f.sha(form), vintages=[str(v) for v in dates])
        return receipt

    def complete_coin_bootstrap(self):
        stamp = self.initial + f.INTERVAL
        receipts = self.observations(stamp, ['100']) + [self.macro_receipt(stamp, eligible=False)]
        state = self.append_receipts(stamp, receipts)
        self.assertFalse(state['engine']['market_bootstrap']); self.assertEqual(state['btc'], '0')
        # Move only the synthetic fixture's relative scheduling anchor. The diary
        # retains its original actual mocked initialization and this baseline event.
        self.initial = stamp
        return state

    def macro_observations(self, stamp, *, eligible=True, missing=()):
        receipts = self.observations(stamp, ['112'], missing=missing)
        bar = next(r for r in receipts if r['category'] == 'bars')
        raw = f.dump([self.bar(stamp // f.INTERVAL * f.INTERVAL - f.INTERVAL, '100')])
        Path(bar['path']).write_bytes(raw); bar['sha256'] = f.sha(raw)
        receipts.append(self.macro_receipt(stamp, eligible=eligible))
        return receipts

'''
s=s.replace(needle,helpers+needle)
s=s.replace("        return self.observe(self.initial + f.INTERVAL, ['112'])\n", "        self.complete_coin_bootstrap()\n        return self.observe(self.initial + f.INTERVAL, ['112'])\n",1)
s=s.replace("        self.initialize(); stamp = self.initial + f.INTERVAL\n        receipts = self.observations(stamp, ['112'])", "        self.initialize(); self.complete_coin_bootstrap(); stamp = self.initial + f.INTERVAL\n        receipts = self.observations(stamp, ['112'])")
s=s.replace("        state = self.initialize(); stamp = self.initial + f.INTERVAL\n        bars =", "        self.initialize(); state = self.complete_coin_bootstrap(); stamp = self.initial + f.INTERVAL\n        bars =")
s=s.replace("        if macro: state['events'] = [{}]  # pure post-bootstrap sizing probe only\n", "")
s=s.replace("        held = self.observe(self.initial + f.INTERVAL, ['113'])\n", "        stamp = self.initial + f.INTERVAL\n        receipts = self.observations(stamp, ['113'])\n        if f.KIND == 'perp': receipts.append(self.macro_receipt(stamp, eligible=False))\n        held = self.append_receipts(stamp, receipts)\n")
needle='    def test_delayed_first_warmup_records_gap_without_past_decisions(self):\n'
regressions='''    @unittest.skipUnless(f.KIND == 'perp', 'Coin actual macro bootstrap completion')
    def test_macro_bootstrap_missing_then_preexisting_consumed_and_fresh_reeligible(self):
        from coinquant.campaign import Campaign
        for deferred in (False, True):
            with self.subTest(deferred=deferred):
                case = ForwardTests(); case.setUp(); self.addCleanup(case.doCleanups)
                initial = case.initialize_deferred() if deferred else case.initialize()
                if deferred:
                    stamp = case.initial + 1000
                    rows = f.strict(f.payload(f.strict(case.history.read_bytes())[0]))
                    case.append_receipts(stamp, [case.receipt('klines?symbol=BTCUSDT&interval=4h', rows, stamp-100)])
                for offset in (1, 2):
                    blocked = case.observe(case.initial + offset * f.INTERVAL, ['100'])
                    self.assertTrue(blocked['engine']['market_bootstrap'])
                    self.assertEqual(blocked['events'][-1]['proposal']['action'], 'blocked')
                    self.assertEqual(blocked['btc'], '0')
                stamp = case.initial + 3 * f.INTERVAL
                receipts = case.macro_observations(stamp)
                row = f.dfii_from(receipts[-1], stamp)
                self.assertLess(row['latest_value_available_ms'], initial['initialized_ms'])
                state = case.append_receipts(stamp, receipts)
                self.assertFalse(state['engine']['market_bootstrap'])
                self.assertEqual(state['events'][-1]['proposal']['action'], 'consumed')
                self.assertEqual(state['events'][-1]['money'], [])
                self.assertEqual(state['wallet'], initial['wallet']); self.assertEqual(state['btc'], '0')
                model = Campaign.restore(state['engine']['campaign'])
                self.assertEqual(model.macro_consumed, model.macro_epoch)
                self.assertTrue(f.audit(f.strict(case.diary.read_bytes())))
                inactive = case.append_receipts(stamp + f.INTERVAL, case.macro_observations(stamp + f.INTERVAL, eligible=False))
                self.assertIsNone(Campaign.restore(inactive['engine']['campaign']).macro_epoch)
                fresh = case.append_receipts(stamp + 2*f.INTERVAL, case.macro_observations(stamp + 2*f.INTERVAL))
                self.assertEqual(fresh['events'][-1]['proposal']['action'], 'enter')
                self.assertGreater(D(fresh['btc']), 0); self.assertTrue(f.audit(f.strict(case.diary.read_bytes())))

    @unittest.skipUnless(f.KIND == 'perp', 'Coin selection checkpoint before book safety')
    def test_macro_bootstrap_persists_on_missing_book_and_selection_failure_is_atomic(self):
        from coinquant.campaign import Campaign
        self.initialize(); stamp = self.initial + f.INTERVAL
        before = self.diary.read_bytes(); bad = self.macro_observations(stamp)
        Path(bad[-1]['form_path']).write_bytes(b'changed raw form')
        with self.assertRaises(ValueError): self.append_receipts(stamp, bad)
        self.assertEqual(before, self.diary.read_bytes())
        first = self.append_receipts(stamp, self.macro_observations(stamp, missing=('depth',)))
        self.assertFalse(first['engine']['market_bootstrap'])
        self.assertEqual(first['events'][-1]['simulated'][0]['status'], 'preview_only')
        consumed = Campaign.restore(first['engine']['campaign']).macro_consumed
        self.assertIsNotNone(consumed); self.assertTrue(f.audit(f.strict(self.diary.read_bytes())))
        second = self.append_receipts(stamp + f.INTERVAL, self.macro_observations(stamp + f.INTERVAL))
        self.assertEqual(Campaign.restore(second['engine']['campaign']).macro_consumed, consumed)
        self.assertEqual(second['events'][-1]['proposal']['action'], 'consumed')
        self.assertEqual(second['btc'], '0'); self.assertEqual(second['fees'], '0')
        self.assertTrue(f.audit(f.strict(self.diary.read_bytes())))

    @unittest.skipUnless(f.KIND == 'perp', 'Coin native repeated primary cold bootstrap')
    def test_pending_macro_bootstrap_reconsumes_primary_until_successful_selection(self):
        from coinquant.campaign import Campaign
        for deferred in (False, True):
            with self.subTest(deferred=deferred):
                case = ForwardTests(); case.setUp(); self.addCleanup(case.doCleanups)
                case.initialize_deferred() if deferred else case.initialize()
                if deferred: case.append_receipts(case.initial + 1000, case.warmup_receipts(case.initial + 1000))
                for offset, close in ((1, '112'), (2, '113')):
                    state = case.observe(case.initial + offset*f.INTERVAL, [close])
                    model = Campaign.restore(state['engine']['campaign'])
                    self.assertTrue(state['engine']['market_bootstrap'])
                    self.assertEqual(model.primary_consumed, model.model.active.identity)
                    self.assertEqual(state['btc'], '0')
                stamp = case.initial + 3*f.INTERVAL
                state = case.append_receipts(stamp, case.observations(stamp, ['114']) + [case.macro_receipt(stamp, eligible=False)])
                self.assertFalse(state['engine']['market_bootstrap']); self.assertEqual(state['btc'], '0')
                case.observe(stamp + f.INTERVAL, ['90'])
                fresh = case.observe(stamp + 2*f.INTERVAL, ['112'])
                self.assertGreater(D(fresh['btc']), 0)  # irrelevant DFII10 remains optional on fresh primary
                self.assertFalse(fresh['engine']['market_bootstrap']); self.assertTrue(f.audit(f.strict(case.diary.read_bytes())))

    @unittest.skipUnless(f.KIND == 'perp', 'Coin strict source-bound bootstrap checkpoint')
    def test_macro_bootstrap_flag_and_checkpoint_tamper_reject_immutably(self):
        initial = self.initialize(); stamp = self.initial + f.INTERVAL
        state = self.append_receipts(stamp, self.macro_observations(stamp))
        for value in (None, 0, 1, 'false', True):
            changed = copy.deepcopy(state); changed['engine']['market_bootstrap'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): f.audit(f.seal(changed))
        changed = copy.deepcopy(state); del changed['engine']['market_bootstrap']
        with self.assertRaises(KeyError): f.audit(f.seal(changed))
        changed = copy.deepcopy(state); changed['engine']['campaign'] = initial['engine']['campaign']
        with self.assertRaises(ValueError): f.audit(f.seal(changed))
        changed = copy.deepcopy(state); changed['events'] = []
        with self.assertRaises(ValueError): f.audit(f.seal(changed))
        # A sealed premature completion cannot be used by a real append either.
        changed = copy.deepcopy(initial); changed['engine']['market_bootstrap'] = False
        self.diary.write_bytes(f.dump(f.seal(changed))); before = self.diary.read_bytes()
        with self.assertRaises(ValueError): self.append_receipts(stamp, self.macro_observations(stamp))
        self.assertEqual(before, self.diary.read_bytes())

'''
assert needle in s;s=s.replace(needle,regressions+needle);p.write_text(s)
(p.parents[2]/'spotquant/tests/test_edge_forward.py').write_text(s)
